#!/usr/bin/env python3
"""
Standalone MCP server that runs Blender in background mode to handle commands.
This runs as a persistent process alongside the Blender GUI container.
"""
import socket
import json
import subprocess
import threading
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

HOST = '0.0.0.0'
PORT = 9876
BLENDER_BIN = '/usr/bin/blender'

class BlenderMCPServer:
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.server_socket = None
        
    def execute_blender_command(self, command_data):
        """Execute a Blender command via background mode"""
        tool = command_data.get('tool', '')
        params = command_data.get('params', {})
        
        # Extract parameters with defaults
        size = params.get('size', 2)
        x = params.get('x', 0)
        y = params.get('y', 0)
        z = params.get('z', 0)
        obj_name = params.get('name', '')
        
        # Create a temporary Python script to execute the command
        script = f"""
import bpy
import json
import sys

result = {{'success': False, 'error': 'Unknown command'}}

try:
    if '{tool}' == 'get_scene_info':
        result = {{
            'success': True,
            'scene_name': bpy.context.scene.name,
            'num_objects': len(bpy.data.objects),
            'render_engine': bpy.context.scene.render.engine
        }}
    elif '{tool}' == 'create_cube':
        bpy.ops.mesh.primitive_cube_add(size={size}, location=({x}, {y}, {z}))
        result = {{'success': True, 'message': 'Cube created'}}
    elif '{tool}' == 'delete_object':
        obj_name = '{obj_name}'
        if obj_name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[obj_name], do_unlink=True)
            result = {{'success': True, 'message': f'Deleted {{obj_name}}'}}
        else:
            result = {{'success': False, 'error': f'Object {{obj_name}} not found'}}
    elif '{tool}' == 'list_objects':
        objects = [obj.name for obj in bpy.data.objects]
        result = {{'success': True, 'objects': objects}}
    elif '{tool}' == 'clear_scene':
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
        result = {{'success': True, 'message': 'Scene cleared'}}
    else:
        result = {{'success': False, 'error': 'Unknown tool: {tool}'}}
except Exception as e:
    result = {{'success': False, 'error': str(e)}}

print('BLENDER_RESULT:' + json.dumps(result))
"""
        
        try:
            # Run Blender in background mode with the script
            cmd = [BLENDER_BIN, '--background', '--python-expr', script]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Parse the result from stdout
            for line in result.stdout.split('\n'):
                if line.startswith('BLENDER_RESULT:'):
                    return json.loads(line.replace('BLENDER_RESULT:', ''))
            
            # If no result found, check for errors
            if result.returncode != 0:
                return {'success': False, 'error': f'Blender exited with code {result.returncode}', 'stderr': result.stderr}
            
            return {'success': False, 'error': 'No result from Blender'}
            
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Command timed out'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def handle_client(self, client_socket, address):
        """Handle a client connection"""
        logger.info(f"New connection from {address}")
        
        try:
            # Receive data
            data = b''
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                data += chunk
                try:
                    # Try to parse as JSON to check if we have complete message
                    json.loads(data.decode('utf-8'))
                    break
                except json.JSONDecodeError:
                    continue
            
            if data:
                command = json.loads(data.decode('utf-8'))
                logger.info(f"Received command: {command.get('tool', 'unknown')}")
                
                # Execute command
                result = self.execute_blender_command(command)
                
                # Send response
                response = json.dumps(result).encode('utf-8')
                client_socket.sendall(response)
                logger.info(f"Sent response: {result.get('success', False)}")
        
        except Exception as e:
            logger.error(f"Error handling client: {e}")
            error_response = json.dumps({'success': False, 'error': str(e)}).encode('utf-8')
            try:
                client_socket.sendall(error_response)
            except:
                pass
        
        finally:
            client_socket.close()
    
    def start(self):
        """Start the TCP server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            logger.info(f"BlenderMCP Server listening on {self.host}:{self.port}")
            
            while True:
                client_socket, address = self.server_socket.accept()
                # Handle each client in a separate thread
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, address))
                client_thread.daemon = True
                client_thread.start()
        
        except KeyboardInterrupt:
            logger.info("Server shutting down...")
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()

if __name__ == '__main__':
    server = BlenderMCPServer()
    server.start()
