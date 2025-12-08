"""
Kubernetes User Session Manager
Manages per-user Blender pods in Kubernetes cluster
"""
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import os
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import random
import time

logger = logging.getLogger(__name__)

@dataclass
class UserBlenderSession:
    """Represents a user's Blender session in Kubernetes"""
    user_id: int
    username: str
    pod_name: str
    service_name: str
    namespace: str
    mcp_port: int
    blender_ui_port: int
    created_at: datetime
    last_activity: datetime
    pod_ip: Optional[str] = None
    external_ip: Optional[str] = None  # LoadBalancer external IP
    blender_ui_url: Optional[str] = None  # External Blender UI URL
    
class K8sUserSessionManager:
    """Manages per-user Blender pods in Kubernetes"""
    
    def __init__(self, namespace: str = "default"):
        """Initialize Kubernetes client"""
        # Try to load in-cluster config first (when running in K8s)
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes config")
        except config.ConfigException:
            # Fall back to local kubeconfig (for development)
            config.load_kube_config()
            logger.info("Loaded local Kubernetes config")
        
        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.networking_v1 = client.NetworkingV1Api()
        self.namespace = namespace
        self.sessions: Dict[int, UserBlenderSession] = {}
        
        # Image to use for Blender pods
        self.blender_image = os.getenv("BLENDER_IMAGE", "prompt2mesh/blender-mcp:latest")
        
        # Get Ingress Controller LoadBalancer IP for nip.io DNS
        self.ingress_ip = self._get_ingress_ip()
        
    def _create_pod_manifest(self, username: str, user_id: int, pod_name: str) -> client.V1Pod:
        """Create Kubernetes pod manifest for user's Blender instance"""
        
        # Container configuration
        container = client.V1Container(
            name="blender-mcp",
            image=self.blender_image,
            image_pull_policy="Always",
            ports=[
                client.V1ContainerPort(container_port=9876, name="mcp", protocol="TCP"),
                client.V1ContainerPort(container_port=3000, name="blender-ui", protocol="TCP")
            ],
            env=[
                client.V1EnvVar(name="BLENDER_PORT", value="9876"),
                client.V1EnvVar(name="MCP_PORT", value="9876"),
                client.V1EnvVar(name="USER_ID", value=str(user_id)),
                client.V1EnvVar(name="USERNAME", value=username),
                # Selkies/web UI configuration - disable HTTPS requirement
                client.V1EnvVar(name="ENABLE_HTTPS", value="false"),
                client.V1EnvVar(name="SELKIES_ENABLE_HTTPS", value="false"),
                client.V1EnvVar(name="SELKIES_ENABLE_BASIC_AUTH", value="false"),
                client.V1EnvVar(name="SELKIES_TURN_PROTOCOL", value="tcp"),
                client.V1EnvVar(name="SELKIES_TURN_SHARED_SECRET", value=""),
                client.V1EnvVar(name="ENABLE_BASIC_AUTH", value="false"),
                # Force legacy mode which doesn't require HTTPS
                client.V1EnvVar(name="SELKIES_MASTER_TOKEN", value=""),
                client.V1EnvVar(name="SELKIES_ENCODER", value="x264enc"),
                client.V1EnvVar(name="SELKIES_ENABLE_RESIZE", value="true"),
                # Allow multiple connections and reconnections (multi-user support)
                client.V1EnvVar(name="SELKIES_ENABLE_MULTI_SEAT", value="true"),
                client.V1EnvVar(name="SELKIES_MAX_CONCURRENT_CONNECTIONS", value="3"),
                client.V1EnvVar(name="SELKIES_IDLE_TIMEOUT", value="0"),  # Disable idle timeout
                client.V1EnvVar(
                    name="ANTHROPIC_API_KEY",
                    value_from=client.V1EnvVarSource(
                        secret_key_ref=client.V1SecretKeySelector(
                            name="api-secrets",
                            key="ANTHROPIC_API_KEY",
                            optional=True
                        )
                    )
                )
            ],
            resources=client.V1ResourceRequirements(
                requests={"cpu": "250m", "memory": "1Gi"},
                limits={"cpu": "2", "memory": "4Gi"}
            ),
            volume_mounts=[
                client.V1VolumeMount(
                    name="blender-data",
                    mount_path="/config"
                )
            ]
        )
        
        # Volume for persistent storage
        volume = client.V1Volume(
            name="blender-data",
            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                claim_name=f"blender-pvc-{username}"
            )
        )
        
        # Pod specification
        pod_spec = client.V1PodSpec(
            containers=[container],
            volumes=[volume],
            restart_policy="Always"
        )
        
        # Pod metadata with labels
        pod_metadata = client.V1ObjectMeta(
            name=pod_name,
            namespace=self.namespace,
            labels={
                "app": "blender-mcp",
                "user": username,
                "user-id": str(user_id),
                "managed-by": "prompt2mesh"
            }
        )
        
        # Complete pod manifest
        pod = client.V1Pod(
            api_version="v1",
            kind="Pod",
            metadata=pod_metadata,
            spec=pod_spec
        )
        
        return pod
    
    def _create_service_manifest(self, username: str, user_id: int, pod_name: str, service_name: str) -> client.V1Service:
        """Create Kubernetes ClusterIP service for user's Blender (accessed via Ingress)"""
        
        # Expose both Blender UI port (3000) and MCP port (9876) as ClusterIP
        service_ports = [
            client.V1ServicePort(
                name="blender-ui",
                port=3000,
                target_port=3000,
                protocol="TCP"
            ),
            client.V1ServicePort(
                name="mcp",
                port=9876,
                target_port=9876,
                protocol="TCP"
            )
        ]
        
        # Service spec - ClusterIP (accessed via Ingress for UI, internally for MCP)
        service_spec = client.V1ServiceSpec(
            selector={
                "app": "blender-mcp",
                "user": username,
                "user-id": str(user_id)
            },
            ports=service_ports,
            type="ClusterIP"
        )
        
        # Service metadata
        service_metadata = client.V1ObjectMeta(
            name=service_name,
            namespace=self.namespace,
            labels={
                "app": "blender-mcp-service",
                "user": username,
                "user-id": str(user_id),
                "managed-by": "prompt2mesh"
            }
        )
        
        # Complete service manifest
        service = client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=service_metadata,
            spec=service_spec
        )
        
        return service
    
    def _create_pvc_manifest(self, username: str) -> client.V1PersistentVolumeClaim:
        """Create PVC for user's Blender data"""
        
        pvc_spec = client.V1PersistentVolumeClaimSpec(
            access_modes=["ReadWriteOnce"],
            resources=client.V1ResourceRequirements(
                requests={"storage": "5Gi"}
            ),
            storage_class_name="gp2"  # AWS EBS for EKS
        )
        
        pvc_metadata = client.V1ObjectMeta(
            name=f"blender-pvc-{username}",
            namespace=self.namespace,
            labels={
                "app": "blender-storage",
                "user": username,
                "managed-by": "prompt2mesh"
            }
        )
        
        pvc = client.V1PersistentVolumeClaim(
            api_version="v1",
            kind="PersistentVolumeClaim",
            metadata=pvc_metadata,
            spec=pvc_spec
        )
        
        return pvc
    
    def _get_ingress_ip(self) -> str:
        """Get the Ingress Controller LoadBalancer IP"""
        try:
            svc = self.core_v1.read_namespaced_service(
                name="ingress-nginx-controller",
                namespace="ingress-nginx"
            )
            if svc.status.load_balancer.ingress:
                ingress = svc.status.load_balancer.ingress[0]
                hostname = ingress.hostname
                if hostname:
                    # Resolve hostname to IP for nip.io
                    import socket
                    ip = socket.gethostbyname(hostname)
                    logger.info(f"Ingress Controller IP: {ip}")
                    return ip
                elif ingress.ip:
                    return ingress.ip
        except Exception as e:
            logger.warning(f"Could not get Ingress IP: {e}")
        
        # Fallback IP if Ingress not ready yet
        return "127.0.0.1"
    
    def _create_ingress_manifest(self, username: str, user_id: int, service_name: str) -> client.V1Ingress:
        """Create Kubernetes Ingress with TLS for user's Blender UI"""
        
        # Use nip.io for DNS (format: blender-username.IP.nip.io)
        host = f"blender-{username}.{self.ingress_ip.replace('.', '-')}.nip.io"
        
        # Ingress path configuration
        path = client.V1HTTPIngressPath(
            path="/",
            path_type="Prefix",
            backend=client.V1IngressBackend(
                service=client.V1IngressServiceBackend(
                    name=service_name,
                    port=client.V1ServiceBackendPort(number=3000)
                )
            )
        )
        
        # HTTP rule for the host
        rule = client.V1IngressRule(
            host=host,
            http=client.V1HTTPIngressRuleValue(paths=[path])
        )
        
        # TLS configuration
        tls = client.V1IngressTLS(
            hosts=[host],
            secret_name=f"blender-{username}-tls"
        )
        
        # Ingress spec
        spec = client.V1IngressSpec(
            ingress_class_name="nginx",
            tls=[tls],
            rules=[rule]
        )
        
        # Ingress metadata with cert-manager annotation
        metadata = client.V1ObjectMeta(
            name=f"blender-ingress-{username}",
            namespace=self.namespace,
            labels={
                "app": "blender-mcp-ingress",
                "user": username,
                "user-id": str(user_id),
                "managed-by": "prompt2mesh"
            },
            annotations={
                # Tell cert-manager to create certificate
                "cert-manager.io/cluster-issuer": "letsencrypt-prod",
                # Configure nginx for WebSocket support (required for Blender web UI)
                "nginx.ingress.kubernetes.io/backend-protocol": "HTTP",
                "nginx.ingress.kubernetes.io/websocket-services": service_name,
                "nginx.ingress.kubernetes.io/proxy-read-timeout": "3600",
                "nginx.ingress.kubernetes.io/proxy-send-timeout": "3600",
            }
        )
        
        ingress = client.V1Ingress(
            api_version="networking.k8s.io/v1",
            kind="Ingress",
            metadata=metadata,
            spec=spec
        )
        
        return ingress
    
    def create_user_session(self, user_id: int, username: str) -> UserBlenderSession:
        """Create a new Blender session (pod) for a user"""
        
        # Check if session already exists
        if user_id in self.sessions:
            session = self.sessions[user_id]
            # Check if pod is still running
            try:
                pod = self.core_v1.read_namespaced_pod(
                    name=session.pod_name,
                    namespace=self.namespace
                )
                if pod.status.phase in ["Running", "Pending"]:
                    logger.info(f"User {username} already has an active session")
                    session.last_activity = datetime.utcnow()
                    return session
                else:
                    # Pod not running, remove old session
                    self._cleanup_session(user_id)
            except ApiException as e:
                if e.status == 404:
                    # Pod doesn't exist, remove old session
                    self._cleanup_session(user_id)
                else:
                    raise
        
        # Generate unique names
        pod_name = f"blender-{username}-{user_id}".lower()
        service_name = f"blender-svc-{username}-{user_id}".lower()
        
        try:
            # 1. Create PVC if it doesn't exist
            pvc_name = f"blender-pvc-{username}"
            try:
                self.core_v1.read_namespaced_persistent_volume_claim(
                    name=pvc_name,
                    namespace=self.namespace
                )
                logger.info(f"PVC {pvc_name} already exists")
            except ApiException as e:
                if e.status == 404:
                    pvc_manifest = self._create_pvc_manifest(username)
                    self.core_v1.create_namespaced_persistent_volume_claim(
                        namespace=self.namespace,
                        body=pvc_manifest
                    )
                    logger.info(f"Created PVC: {pvc_name}")
                else:
                    raise
            
            # 2. Create Pod (or use existing one)
            pod = None
            try:
                # Check if pod already exists
                pod = self.core_v1.read_namespaced_pod(
                    name=pod_name,
                    namespace=self.namespace
                )
                if pod.status.phase in ["Running", "Pending"]:
                    logger.info(f"Pod {pod_name} already exists and is {pod.status.phase}")
                else:
                    # Pod exists but not running, delete and recreate
                    logger.warning(f"Pod {pod_name} exists but is {pod.status.phase}, deleting...")
                    self.core_v1.delete_namespaced_pod(name=pod_name, namespace=self.namespace)
                    time.sleep(3)
                    pod = None
            except ApiException as e:
                if e.status == 404:
                    # Pod doesn't exist, will create it
                    pod = None
                else:
                    raise
            
            # Create pod if it doesn't exist
            if not pod:
                pod_manifest = self._create_pod_manifest(username, user_id, pod_name)
                pod = self.core_v1.create_namespaced_pod(
                    namespace=self.namespace,
                    body=pod_manifest
                )
                logger.info(f"Created pod: {pod_name}")
            
            # 3. Create Service (delete existing one if it exists)
            try:
                self.core_v1.read_namespaced_service(
                    name=service_name,
                    namespace=self.namespace
                )
                # Service exists, delete it first
                logger.warning(f"Service {service_name} already exists, deleting it first")
                self.core_v1.delete_namespaced_service(
                    name=service_name,
                    namespace=self.namespace
                )
                # Wait a moment for deletion
                time.sleep(2)
            except ApiException as e:
                if e.status != 404:
                    raise
            
            service_manifest = self._create_service_manifest(username, user_id, pod_name, service_name)
            service = self.core_v1.create_namespaced_service(
                namespace=self.namespace,
                body=service_manifest
            )
            logger.info(f"Created service: {service_name}")
            
            # 4. Create Ingress with TLS (or use existing one)
            ingress_name = f"blender-ingress-{username}"
            ingress_host = f"blender-{username}.{self.ingress_ip.replace('.', '-')}.nip.io"
            try:
                # Check if ingress already exists
                ingress = self.networking_v1.read_namespaced_ingress(
                    name=ingress_name,
                    namespace=self.namespace
                )
                logger.info(f"Ingress {ingress_name} already exists")
            except ApiException as e:
                if e.status == 404:
                    # Ingress doesn't exist, create it
                    ingress_manifest = self._create_ingress_manifest(username, user_id, service_name)
                    ingress = self.networking_v1.create_namespaced_ingress(
                        namespace=self.namespace,
                        body=ingress_manifest
                    )
                    logger.info(f"Created ingress: {ingress_name}, host: {ingress_host}")
                else:
                    raise
            
            # 5. Wait for pod to get IP
            pod_ip = None
            for _ in range(30):  # Wait up to 30 seconds
                try:
                    pod = self.core_v1.read_namespaced_pod(
                        name=pod_name,
                        namespace=self.namespace
                    )
                    if pod.status.pod_ip:
                        pod_ip = pod.status.pod_ip
                        break
                except ApiException:
                    pass
                time.sleep(1)
            
            # Blender UI URL with HTTPS via Ingress
            blender_ui_url = f"https://{ingress_host}"
            external_ip = ingress_host  # Use hostname as "external IP" for compatibility
            
            logger.info(f"Blender UI will be available at: {blender_ui_url}")
            logger.info(f"Certificate provisioning may take 60-120 seconds...")
            
            # Create session object
            session = UserBlenderSession(
                user_id=user_id,
                username=username,
                pod_name=pod_name,
                service_name=service_name,
                namespace=self.namespace,
                mcp_port=9876,  # Internal port
                blender_ui_port=3000,  # Internal port
                created_at=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                pod_ip=pod_ip,
                external_ip=external_ip,
                blender_ui_url=blender_ui_url
            )
            
            self.sessions[user_id] = session
            logger.info(f"Created session for user {username} (ID: {user_id})")
            
            return session
            
        except ApiException as e:
            logger.error(f"Failed to create Kubernetes resources for user {username}: {e}")
            raise Exception(f"Failed to create Blender session: {e.reason}")
    
    def get_user_session(self, user_id: int) -> Optional[UserBlenderSession]:
        """Get existing user session"""
        return self.sessions.get(user_id)
    
    def stop_user_session(self, user_id: int) -> bool:
        """Stop user's Blender session (but keep resources for restart)"""
        if user_id not in self.sessions:
            return False
        
        session = self.sessions[user_id]
        
        try:
            # Scale down by deleting pod (service remains for restart)
            self.core_v1.delete_namespaced_pod(
                name=session.pod_name,
                namespace=self.namespace
            )
            logger.info(f"Stopped pod for user {session.username}")
            return True
        except ApiException as e:
            logger.error(f"Failed to stop session: {e}")
            return False
    
    def remove_user_session(self, user_id: int) -> bool:
        """Remove user's Blender session completely"""
        session = self.sessions.get(user_id)
        
        # If no session in memory, try to find resources by label
        if not session:
            logger.info(f"No session in memory for user {user_id}, searching for resources by label...")
            try:
                # Find pods with matching user-id label
                pods = self.core_v1.list_namespaced_pod(
                    namespace=self.namespace,
                    label_selector=f"app=blender-mcp,user-id={user_id}"
                )
                
                # Find services with matching user-id label
                services = self.core_v1.list_namespaced_service(
                    namespace=self.namespace,
                    label_selector=f"app=blender-mcp-service,user-id={user_id}"
                )
                
                # Find ingresses with matching user-id label
                ingresses = self.networking_v1.list_namespaced_ingress(
                    namespace=self.namespace,
                    label_selector=f"app=blender-mcp-ingress,user-id={user_id}"
                )
                
                deleted_something = False
                
                # Delete all matching pods
                for pod in pods.items:
                    try:
                        self.core_v1.delete_namespaced_pod(
                            name=pod.metadata.name,
                            namespace=self.namespace
                        )
                        logger.info(f"Deleted pod: {pod.metadata.name}")
                        deleted_something = True
                    except ApiException as e:
                        if e.status != 404:
                            logger.warning(f"Failed to delete pod {pod.metadata.name}: {e}")
                
                # Delete all matching services
                for svc in services.items:
                    try:
                        self.core_v1.delete_namespaced_service(
                            name=svc.metadata.name,
                            namespace=self.namespace
                        )
                        logger.info(f"Deleted service: {svc.metadata.name}")
                        deleted_something = True
                    except ApiException as e:
                        if e.status != 404:
                            logger.warning(f"Failed to delete service {svc.metadata.name}: {e}")
                
                # Delete all matching ingresses
                for ing in ingresses.items:
                    try:
                        self.networking_v1.delete_namespaced_ingress(
                            name=ing.metadata.name,
                            namespace=self.namespace
                        )
                        logger.info(f"Deleted ingress: {ing.metadata.name}")
                        deleted_something = True
                    except ApiException as e:
                        if e.status != 404:
                            logger.warning(f"Failed to delete ingress {ing.metadata.name}: {e}")
                
                return deleted_something
                
            except Exception as e:
                logger.error(f"Error searching for resources to delete: {e}")
                return False
        
        # Session exists in memory - use it
        try:
            # Delete pod
            try:
                self.core_v1.delete_namespaced_pod(
                    name=session.pod_name,
                    namespace=self.namespace
                )
                logger.info(f"Deleted pod: {session.pod_name}")
            except ApiException as e:
                if e.status != 404:
                    logger.warning(f"Failed to delete pod: {e}")
            
            # Delete service
            try:
                self.core_v1.delete_namespaced_service(
                    name=session.service_name,
                    namespace=self.namespace
                )
                logger.info(f"Deleted service: {session.service_name}")
            except ApiException as e:
                if e.status != 404:
                    logger.warning(f"Failed to delete service: {e}")
            
            # Delete ingress
            try:
                ingress_name = f"blender-ingress-{session.username}"
                self.networking_v1.delete_namespaced_ingress(
                    name=ingress_name,
                    namespace=self.namespace
                )
                logger.info(f"Deleted ingress: {ingress_name}")
            except ApiException as e:
                if e.status != 404:
                    logger.warning(f"Failed to delete ingress: {e}")
            
            # Note: We keep the PVC for data persistence
            # It can be manually cleaned up later if needed
            
            # Remove from sessions
            del self.sessions[user_id]
            logger.info(f"Removed session for user {session.username}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error removing session: {e}")
            return False
    
    def _cleanup_session(self, user_id: int):
        """Internal cleanup of session data"""
        if user_id in self.sessions:
            del self.sessions[user_id]
    
    def get_mcp_connection_url(self, user_id: int) -> Optional[str]:
        """Get MCP connection URL for user's Blender instance"""
        session = self.get_user_session(user_id)
        if not session:
            return None
        
        # Use service name for DNS-based access within cluster
        return f"{session.service_name}.{self.namespace}.svc.cluster.local:{session.mcp_port}"
    
    def get_blender_ui_url(self, user_id: int) -> Optional[str]:
        """Get Blender UI URL (requires ingress/NodePort configuration)"""
        session = self.get_user_session(user_id)
        if not session:
            return None
        
        # This would need to be exposed via Ingress
        # For now, return the internal service URL
        return f"http://{session.service_name}.{self.namespace}.svc.cluster.local:{session.blender_ui_port}"
    
    def list_active_sessions(self) -> list:
        """List all active user sessions"""
        return list(self.sessions.values())
    
    def cleanup_stale_sessions(self, max_age_hours: int = 24):
        """Clean up sessions older than max_age_hours"""
        current_time = datetime.utcnow()
        stale_users = []
        
        for user_id, session in self.sessions.items():
            age = (current_time - session.last_activity).total_seconds() / 3600
            if age > max_age_hours:
                stale_users.append(user_id)
        
        for user_id in stale_users:
            logger.info(f"Cleaning up stale session for user {user_id}")
            self.remove_user_session(user_id)
