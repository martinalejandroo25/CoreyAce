# CoreyAce

Asistente de escritorio modular en Python con soporte para modelos de lenguaje online (Gemini, OpenAI, Anthropic) y locales (Ollama/Llama 3), asi como sintesis de voz (ElevenLabs y ChatTTS).

## Estructura

- `ace_assistant/main.py`: Punto de entrada del asistente.
- `ace_assistant/core/`: Logica de integracion de LLM y gestion de estado.
- `ace_assistant/tools/`: Herramientas de ejecucion y comandos del sistema.
- `ace_assistant/ui/`: Interfaz grafica de usuario.
- `ace_assistant/config.json.example`: Plantilla de configuracion JSON.

## Instalacion y Uso

1. Crear y activar entorno virtual:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Instalar dependencias:
   ```bash
   pip install -r ace_assistant/requirements.txt
   ```
3. Configurar credenciales:
   Copiar `ace_assistant/config.json.example` a `ace_assistant/config.json` y/o `.env.example` a `.env`.
4. Ejecutar:
   ```bash
   python ace_assistant/main.py
   ```
