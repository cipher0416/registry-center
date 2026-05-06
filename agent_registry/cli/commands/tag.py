"""
Tag Management Commands

Manage agent tags via UDS (Unix Domain Socket) internal service.
"""

import json
import socket
from argparse import ArgumentParser, Namespace
from typing import Dict, Optional, List

from agent_registry.cli import BaseCommand, CLI, Output, cli_logger
from agent_registry.cli.exceptions import ServiceError, CLIError


UDS_SOCKET_PATH = "run/registry-center/internal.sock"


class UDSClient:
    """
    UDS Client for internal service
    
    Connects to Unix Domain Socket to call internal handlers.
    """
    
    def __init__(self, socket_path: Optional[str] = None):
        self.socket_path = socket_path or UDS_SOCKET_PATH
    
    def send_request(self, action: str, params: Dict) -> Dict:
        """
        Send request to UDS service
        
        Args:
            action: Action name (e.g., 'tag_add', 'tag_get')
            params: Request parameters
            
        Returns:
            Response dict with success, message, data, error
            
        Raises:
            ServiceError: If connection fails or request fails
        """
        client_socket = None
        try:
            client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client_socket.connect(self.socket_path)
            
            request = {
                "action": action,
                "params": params
            }
            
            client_socket.send(json.dumps(request).encode('utf-8'))
            
            response_data = client_socket.recv(4096)
            response = json.loads(response_data.decode('utf-8'))
            
            return response
            
        except FileNotFoundError:
            raise ServiceError(
                f"UDS socket not found at {self.socket_path}.\n"
                "Please ensure the service is running."
            )
        except ConnectionRefusedError:
            raise ServiceError(
                f"Connection refused. Service may not be running.\n"
                f"Socket path: {self.socket_path}"
            )
        except Exception as e:
            raise ServiceError(f"UDS connection error: {e}")
        finally:
            if client_socket:
                client_socket.close()


def get_tag_client() -> UDSClient:
    """Get UDS client instance"""
    return UDSClient()


@CLI.register
class TagCommand(BaseCommand):
    """Tag management command group"""
    
    @property
    def name(self) -> str:
        return "tag"
    
    @property
    def help_text(self) -> str:
        return "Agent tag management via UDS interface"
    
    @property
    def subcommands(self) -> Dict[str, BaseCommand]:
        return {
            "add": TagAddCommand(),
            "remove": TagRemoveCommand(),
            "update": TagUpdateCommand(),
            "get": TagGetCommand(),
            "list": TagListCommand(),
        }
    
    def execute(self, args: Namespace) -> int:
        return 0


class TagAddCommand(BaseCommand):
    """Add tags to agent"""
    
    @property
    def name(self) -> str:
        return "add"
    
    @property
    def help_text(self) -> str:
        return "Add tags to agent"
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("name", help="Agent name")
        parser.add_argument("--org", "-o", required=True, help="Organization name")
        parser.add_argument("--tags", "-t", required=True, nargs='+', help="Tags to add (space-separated)")
        parser.add_argument("--format", "-f", choices=["text", "json"], default="text")
    
    def execute(self, args: Namespace) -> int:
        client = get_tag_client()
        output = Output(args.format)
        
        try:
            result = client.send_request("tag_add", {
                "agent_name": args.name,
                "organization": args.org,
                "tags": args.tags
            })
            
            if result.get("success"):
                if args.format == "json":
                    output.print(result)
                else:
                    tags = result.get("data", {}).get("tags", [])
                    output.success(f"Tags added successfully")
                    output.info(f"Current tags: {', '.join(tags)}")
                return 0
            else:
                output.error(result.get("error", "Unknown error"))
                return 1
        
        except ServiceError as e:
            output.error(str(e))
            return e.exit_code


class TagRemoveCommand(BaseCommand):
    """Remove tags from agent"""
    
    @property
    def name(self) -> str:
        return "remove"
    
    @property
    def help_text(self) -> str:
        return "Remove tags from agent"
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("name", help="Agent name")
        parser.add_argument("--org", "-o", required=True, help="Organization name")
        parser.add_argument("--tags", "-t", required=True, nargs='+', help="Tags to remove (space-separated)")
        parser.add_argument("--format", "-f", choices=["text", "json"], default="text")
    
    def execute(self, args: Namespace) -> int:
        client = get_tag_client()
        output = Output(args.format)
        
        try:
            result = client.send_request("tag_remove", {
                "agent_name": args.name,
                "organization": args.org,
                "tags": args.tags
            })
            
            if result.get("success"):
                if args.format == "json":
                    output.print(result)
                else:
                    tags = result.get("data", {}).get("tags", [])
                    output.success(f"Tags removed successfully")
                    output.info(f"Remaining tags: {', '.join(tags) if tags else 'none'}")
                return 0
            else:
                output.error(result.get("error", "Unknown error"))
                return 1
        
        except ServiceError as e:
            output.error(str(e))
            return e.exit_code


class TagUpdateCommand(BaseCommand):
    """Update agent tags (full replacement)"""
    
    @property
    def name(self) -> str:
        return "update"
    
    @property
    def help_text(self) -> str:
        return "Update agent tags (full replacement)"
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("name", help="Agent name")
        parser.add_argument("--org", "-o", required=True, help="Organization name")
        parser.add_argument("--tags", "-t", required=True, nargs='+', help="New tags (space-separated)")
        parser.add_argument("--format", "-f", choices=["text", "json"], default="text")
    
    def execute(self, args: Namespace) -> int:
        client = get_tag_client()
        output = Output(args.format)
        
        try:
            result = client.send_request("tag_update", {
                "agent_name": args.name,
                "organization": args.org,
                "tags": args.tags
            })
            
            if result.get("success"):
                if args.format == "json":
                    output.print(result)
                else:
                    tags = result.get("data", {}).get("tags", [])
                    output.success(f"Tags updated successfully")
                    output.info(f"New tags: {', '.join(tags)}")
                return 0
            else:
                output.error(result.get("error", "Unknown error"))
                return 1
        
        except ServiceError as e:
            output.error(str(e))
            return e.exit_code


class TagGetCommand(BaseCommand):
    """Get agent tags"""
    
    @property
    def name(self) -> str:
        return "get"
    
    @property
    def help_text(self) -> str:
        return "Get agent tags"
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("name", help="Agent name")
        parser.add_argument("--org", "-o", required=True, help="Organization name")
        parser.add_argument("--format", "-f", choices=["text", "json"], default="text")
    
    def execute(self, args: Namespace) -> int:
        client = get_tag_client()
        output = Output(args.format)
        
        try:
            result = client.send_request("tag_get", {
                "agent_name": args.name,
                "organization": args.org
            })
            
            if result.get("success"):
                if args.format == "json":
                    output.print(result)
                else:
                    tags = result.get("data", {}).get("tags", [])
                    if tags:
                        output.info(f"Tags for '{args.name}': {', '.join(tags)}")
                    else:
                        output.info(f"Agent '{args.name}' has no tags")
                return 0
            else:
                output.error(result.get("error", "Unknown error"))
                return 1
        
        except ServiceError as e:
            output.error(str(e))
            return e.exit_code


class TagListCommand(BaseCommand):
    """List agents by tag"""
    
    @property
    def name(self) -> str:
        return "list"
    
    @property
    def help_text(self) -> str:
        return "List agents with specific tag"
    
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("tag", help="Tag to search")
        parser.add_argument("--format", "-f", choices=["text", "json"], default="text")
    
    def execute(self, args: Namespace) -> int:
        client = get_tag_client()
        output = Output(args.format)
        
        try:
            result = client.send_request("tag_list", {
                "tag": args.tag
            })
            
            if result.get("success"):
                if args.format == "json":
                    output.print(result)
                else:
                    agents = result.get("data", {}).get("agents", [])
                    count = result.get("data", {}).get("count", 0)
                    
                    if agents:
                        output.info(f"Found {count} agents with tag '{args.tag}':")
                        for agent in agents:
                            name = agent.get("agent_name", "unknown")
                            org = agent.get("organization", "unknown")
                            desc = agent.get("description", "")
                            if desc:
                                desc = desc[:50] + "..." if len(desc) > 50 else desc
                            print(f"  {name} ({org}) - {desc}")
                    else:
                        output.info(f"No agents found with tag '{args.tag}'")
                return 0
            else:
                output.error(result.get("error", "Unknown error"))
                return 1
        
        except ServiceError as e:
            output.error(str(e))
            return e.exit_code