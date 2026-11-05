# Componentes de terceiros

| Componente | Uso | Licença |
|---|---|---|
| Ollama | executa a IA local | MIT |
| Qwen3 (modelos) | conversa e resumos | Apache 2.0 |
| bge-m3 | busca por significado | MIT |
| faster-whisper / CTranslate2 | reconhecimento de voz | MIT |
| Whisper large-v3-turbo (modelo) | reconhecimento de voz | MIT |
| Kokoro-82M e kokoro-onnx | voz (Dora, Alex, Santa) | Apache 2.0 / MIT |
| espeak-ng (via espeakng-loader) | pronúncia da Kokoro | GPL-3.0 (executado como biblioteca separada) |
| Piper (piper-tts) e vozes | voz alternativa | GPL-3.0 (piper-tts); vozes com licença própria |
| Vosk (opcional) | voz básica | Apache 2.0 |
| pywebview, keyring, icalendar, recurring-ical-events, numpy, cryptography | aplicativo | BSD/MIT/Apache |

**Atenção para a venda:** o `piper-tts` e o `espeak-ng` são GPL-3.0. Na **edição comercial** (`"edicao": "comercial"` no config), o instalador não instala o Piper e mostra apenas as vozes Kokoro. O `espeak-ng` é usado pela Kokoro como biblioteca separada. Antes de vender em escala, confirme com um advogado como as licenças se aplicam à sua forma de distribuição. A alternativa mais segura é entregar o código-fonte junto ou instalar esses componentes à parte, durante a instalação.

O FreeLLMAPI **não** é incluído. Ele se declara "apenas para experimentação pessoal".
