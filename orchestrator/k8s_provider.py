import logging
import os
import time
import requests
from kubernetes import client, config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class K8sProvider:
    def __init__(self):
        self.namespace = os.getenv('K8s_NAMESPACE', 'default')
        self.minikube_ip = os.getenv('MINIKUBE_IP', '192.168.49.2')
        try:
            try:
                config.load_incluster_config()
                logger.info("Loaded in-cluster K8s config")
            except:
                config.load_kube_config()
                logger.info("Loaded K8s config from kubeconfig file")
            self.core_v1 = client.CoreV1Api()
            logger.info(f"K8s Provider initialized (namespace: {self.namespace})")
        except Exception as e:
            logger.error(f"Failed to initialize K8s Provider: {e}")
            logger.error("Make sure Kubernetes is running. For local development, run: minikube start")
            logger.error("See .agent/workflows/setup-minikube.md for setup instructions")
            raise

    def wait_for_health(self, url, timeout=30):
        """Poll the health endpoint until it returns 200 OK."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{url}/health", timeout=2)
                if response.status_code == 200:
                    return True
            except requests.RequestException:
                pass
            time.sleep(1)
        return False

    def get_pod_name(self, user_id):
        return f"blender-{user_id}"

    def get_instance_url(self, user_id):
        pod_name = self.get_pod_name(user_id)
        service_name = f"service-{user_id}"
        try:
            # Check if pod is running
            pod = self.core_v1.read_namespaced_pod(name=pod_name, namespace=self.namespace)
            if pod.status.phase != 'Running':
                return None
            
            # Get Service NodePort
            service = self.core_v1.read_namespaced_service(name=service_name, namespace=self.namespace)
            node_port = service.spec.ports[0].node_port
            return f"http://{self.minikube_ip}:{node_port}"
        except client.exceptions.ApiException as e:
            if e.status == 404:
                return None
            raise

    def get_instance_info(self, user_id):
        pod_name = self.get_pod_name(user_id)
        status = "stopped"
        url = None
        try:
            pod = self.core_v1.read_namespaced_pod(name=pod_name, namespace=self.namespace)
            status = pod.status.phase.lower()
            if status == 'running':
                # Try to get service URL
                url = self.get_instance_url(user_id)
        except client.exceptions.ApiException as e:
            if e.status == 404:
                status = "not_found"
            else:
                status = "error"
        
        return {
            "instance_id": pod_name,
            "status": status,
            "url": url,
            "provider": "k8s"
        }

    def spawn_instance(self, user_id):
        existing_url = self.get_instance_url(user_id)
        if existing_url:
            if self.wait_for_health(existing_url, timeout=5):
                return existing_url
            return existing_url

        pod_name = self.get_pod_name(user_id)
        logger.info(f"Spawning K8s pod {pod_name}")
        
        pod_manifest = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": pod_name,
                "labels": {"app": "blender-mcp", "user": user_id}
            },
            "spec": {
                "containers": [{
                    "name": "blender-mcp",
                    "image": "blender-mcp:latest",
                    "imagePullPolicy": "IfNotPresent",
                    "ports": [{"containerPort": 8080}],
                    "env": [{"name": "PORT", "value": "8080"}]
                }],
                "restartPolicy": "Never"
            }
        }

        service_manifest = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": f"service-{user_id}"
            },
            "spec": {
                "selector": {
                    "app": "blender-mcp",
                    "user": user_id
                },
                "ports": [{
                    "protocol": "TCP",
                    "port": 8080,
                    "targetPort": 8080,
                    "nodePort": 0  # Let K8s assign a port
                }],
                "type": "NodePort"
            }
        }

        try:
            self.core_v1.create_namespaced_pod(body=pod_manifest, namespace=self.namespace)
            self.core_v1.create_namespaced_service(body=service_manifest, namespace=self.namespace)
            
            # Wait for IP
            url = None
            for _ in range(30):
                url = self.get_instance_url(user_id)
                if url:
                    break
                time.sleep(1)
            
            if not url:
                raise Exception("Timeout waiting for Pod IP")

            # Wait for health
            if self.wait_for_health(url, timeout=60):
                return url
            
            raise Exception("Pod failed to pass health check")
            
        except Exception as e:
            logger.error(f"Failed to create pod: {e}")
            raise

    def despawn_instance(self, user_id):
        """Delete the Blender instance pod for the given user."""
        pod_name = self.get_pod_name(user_id)
        logger.info(f"Despawning K8s pod {pod_name}")
        
        try:
            self.core_v1.delete_namespaced_pod(
                name=pod_name,
                namespace=self.namespace,
                body=client.V1DeleteOptions()
            )
            try:
                self.core_v1.delete_namespaced_service(
                    name=f"service-{user_id}",
                    namespace=self.namespace,
                    body=client.V1DeleteOptions()
                )
            except client.exceptions.ApiException:
                pass # Ignore if service doesn't exist
            logger.info(f"Successfully deleted pod {pod_name}")
            return True
        except client.exceptions.ApiException as e:
            if e.status == 404:
                logger.warning(f"Pod {pod_name} not found, already deleted")
                return False
            else:
                logger.error(f"Failed to delete pod {pod_name}: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error deleting pod {pod_name}: {e}")
            raise
