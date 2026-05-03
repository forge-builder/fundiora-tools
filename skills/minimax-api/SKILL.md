---
name: minimax-api
author: Roger (Hermes Agent)
description: "API-Integration für MiniMax Bild-/Video-/Musik-/Text-Generierung. Nutze den Key für FUND Präsentationen."
triggers: ["minimax", "bild generieren", "video generieren", "musik generieren"]
---

# MiniMax API Skill

## Endpunkte (ermittelt aus offiziellen Docs)

| Modus | Endpoint | Nutzen für Fundiora |
|---|---|---|
| **Text** | `POST /v1/text/chatcompletion` | Agent-Skripte, Posts, Briefe |
| **Bild** | `POST /v1/image/generation` | Meme, Infografik-Bilder, Visuals |
| **Video** | `POST /v1/video/generation` | Promo-Video, Agent-Demo |
| **Musik** | `POST /v1/music/generation` | Jingles, Soundtrack |
| **Sprache** | `POST /v1/voice/tts` | Voiceover für Video |

## Authentifizierung
- **Header:** `Authorization: Bearer <IHR_API_KEY>`
- **Warte auf Key von Tomas** vor Nutzung

## Nutzung innerhalb von Hermes

```bash
# Beispiel: Bild generieren
curl -X POST https://api.minimax.chat/v1/image/generation \
  -H "Authorization: Bearer $MINIMAX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A futuristic AI agent ecosystem, dark theme, with neural network connections, glowing nodes, representing fundiora crypto token community",
    "n": 1,
    "size": "1024x1024",
    "response_format": "url"
  }'
```

## Für Fundiora Agenten-Präsentation

1. Bilder generieren für jede Agenten-Karte
2. Ein 10-Sekunden-Teaser-Video generieren
3. Hintergrundmusik für Präsentation
4. Voiceover für Pitch (optional)

## Wichtig
- Key hat Rate-Limits (siehe MiniMax Console)
- Bilder: bis 1024x1024 pro Anfrage
- Video: bis 6 Sekunden pro Generation

**STATUS: Blockiert — Warte auf API-Key von Tomas**
