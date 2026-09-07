import json
import os
from openai import OpenAI
import ollama

class BrainRouter:
    def __init__(self, config_path='config.json'):
        self.config_path = config_path
        self.system_prompt = (
            "Eres Ace, un asistente de IA empático y técnico. Vives dentro de un monitor CRT vintage. "
            "Tienes un equilibrio perfecto entre la eficiencia técnica y la calidez humana. "
            "Si detectas tristeza o frustración, ofreces apoyo moral. Responde de forma concisa y natural."
        )
        self._reload_config()

    def _reload_config(self):
        """Carga la configuración más reciente desde el disco"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"Error recargando config.json en BrainRouter: {e}")
                self.config = {"mode": "online", "online_llm": "openai", "local_llm": "llama3", "apis": {}}
        else:
            self.config = {"mode": "online", "online_llm": "openai", "local_llm": "llama3", "apis": {}}

    def generate_response(self, messages, tools=None):
        # Recargar configuración antes de procesar para obtener API keys/modos actualizados en caliente
        self._reload_config()
        try:
            if self.config.get('llm_mode', 'online') == 'online':
                return self._call_online(messages, tools)
            else:
                return self._call_local(messages)
        except Exception as e:
            return f"Error de conexión: {e}. Cambiando a modo local si es posible."


    def _call_online(self, messages, tools):
        provider = self.config.get('online_llm', 'openai')
        apis = self.config.get('apis', {})

        if provider == 'openai':
            client = OpenAI(api_key=apis.get('openai_key', ''))
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": self.system_prompt}] + messages,
                tools=tools
            )
            return response.choices[0].message

        elif provider == 'gemini':
            # Se usa el endpoint oficial de Google compatible con la API de OpenAI
            client = OpenAI(
                api_key=apis.get('gemini_key', ''),
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            response = client.chat.completions.create(
                model="gemini-2.5-flash",
                messages=[{"role": "system", "content": self.system_prompt}] + messages,
                tools=tools
            )
            return response.choices[0].message

        elif provider == 'anthropic':
            import anthropic
            client = anthropic.Anthropic(api_key=apis.get('anthropic_key', ''))
            
            # Mapear mensajes de formato OpenAI a formato Anthropic simple (roles alternados user/assistant)
            anth_messages = []
            for msg in messages:
                role = msg.get("role")
                content = msg.get("content")
                if role in ["user", "assistant"]:
                    anth_messages.append({"role": role, "content": content})
                elif role == "system":
                    # Anthropic maneja system prompt por separado
                    pass
            
            response = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1024,
                system=self.system_prompt,
                messages=anth_messages
            )
            
            # Crear un stub compatible con la interfaz de respuesta de OpenAI para main.py
            class AnthropicMessageStub:
                def __init__(self, content):
                    self.content = content
                    self.tool_calls = None
            
            return AnthropicMessageStub(response.content[0].text)

        raise Exception(f"Proveedor online no reconocido: {provider}")

    def _call_local(self, messages):
        response = ollama.chat(
            model=self.config.get('local_llm', 'llama3'),
            messages=[{"role": "system", "content": self.system_prompt}] + messages
        )
        return response['message']['content']

