# core/agent.py
# Definimos las herramientas en formato OpenAI
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Obtiene la hora y fecha actual",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Abre una aplicación en el sistema operativo",
            "parameters": {
                "type": "object",
                "properties": {"app_name": {"type": "string", "description": "Nombre de la app"}}
            },
            "required": ["app_name"]
        }
    }
]

def execute_tool(tool_name, arguments):
    from tools.os_tools import get_current_time, open_application
    if tool_name == "get_current_time": return get_current_time()
    if tool_name == "open_application": return open_application(arguments.get("app_name"))
    return "Herramienta no reconocida."
