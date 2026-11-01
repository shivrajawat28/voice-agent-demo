/**
 * ConversationEngine
 *
 * Deterministic offline conversation engine for FertoBot Voice Agent Demo.
 * Maps normalized natural language input to configured intents and predictable responses.
 * Supports bilingual responses (English and Hindi) for voice clarity testing.
 *
 * NOTE: This is an offline mock/deterministic brain for Phase 2-5 validation,
 * NOT a live LLM or external API.
 */

import { EngineResponse, IntentType } from '../types/voiceAgent';

export interface IntentRule {
  intent: IntentType;
  patterns: RegExp[];
  generateResponse: (engine: ConversationEngine, matchedInput: string) => string;
  repeatable: boolean;
}

export class ConversationEngine {
  private lastAgentResponse: string | null = null;
  private readonly rules: IntentRule[];

  constructor() {
    this.rules = [
      // 1. Greeting
      {
        intent: 'greeting',
        patterns: [
          /^(hello|hi|hey|greetings|namaste|ram\s*ram|good\s*(morning|afternoon|evening))\b/i,
          /\b(hello|hi|hey|namaste)\b/i,
          /(नमस्ते|नमस्कार|प्रणाम|राम\s*राम)/,
        ],
        generateResponse: (_, input) => {
          const isHindi = /[\u0900-\u097F]/.test(input);
          return isHindi
            ? 'नमस्ते! मैं आपका फर्तोबॉट वॉइस असिस्टेंट हूँ। आज मैं आपके खेत की क्या मदद कर सकता हूँ?'
            : 'Hello! I am your FertoBot Voice Assistant running in local demo mode. How can I help your farm today?';
        },
        repeatable: true,
      },

      // 2. Agent Introduction
      {
        intent: 'intro',
        patterns: [
          /\b(who\s+are\s+you|what\s+is\s+your\s+name|introduce\s+yourself|tell\s+me\s+about\s+yourself)\b/i,
          /(आप\s*कौन\s*हैं|तुम्हारा\s*नाम\s*क्या\s*है|अपना\s*परिचय)/,
        ],
        generateResponse: (_, input) => {
          const isHindi = /[\u0900-\u097F]/.test(input);
          return isHindi
            ? 'मैं फर्तोबॉट वॉइस एजेंट हूँ, एक एआई कृषि सहायक डेमो। मैं किसानों को खेत की टेलीमेट्री और फसल परामर्श में मदद करता हूँ।'
            : 'I am FertoBot Voice Agent, an AI farm assistant demo. I help growers check telemetry, explore crop recommendations, and answer farm queries.';
        },
        repeatable: true,
      },

      // 3. Help / Capabilities
      {
        intent: 'help',
        patterns: [
          /\b(what\s+can\s+you\s+do|help|options|commands|show\s+help|capabilities)\b/i,
          /(मदद|सहायता|तुम\s*क्या\s*कर\s*सकते\s*हो)/,
        ],
        generateResponse: (_, input) => {
          const isHindi = /[\u0900-\u097F]/.test(input);
          return isHindi
            ? 'आप कह सकते हैं: "नमस्ते", "आप कौन हैं?", "खेत की स्थिति", "दोहराएं", या "अलविदा"।'
            : 'You can say: "Hello", "Who are you?", "Farm status", "Repeat", or "Goodbye". You can also test text input if your microphone is unavailable.';
        },
        repeatable: true,
      },

      // 4. Repeat
      {
        intent: 'repeat',
        patterns: [
          /\b(repeat|say\s+that\s+again|what\s+did\s+you\s+say|repeat\s+last|one\s+more\s+time)\b/i,
          /(दोहराएं|फिर\s*से\s*बोलो|दोबारा\s*कहो)/,
        ],
        generateResponse: (engine, input) => {
          const isHindi = /[\u0900-\u097F]/.test(input);
          if (engine.lastAgentResponse) {
            return isHindi
              ? `दोहरा रहा हूँ: "${engine.lastAgentResponse}"`
              : `Repeating: "${engine.lastAgentResponse}"`;
          }
          return isHindi
            ? "मैंने अभी तक कुछ नहीं कहा है! शुरू करने के लिए 'नमस्ते' कहें।"
            : "I haven't said anything yet to repeat! Say 'Hello' or ask 'Who are you?' to begin.";
        },
        repeatable: false,
      },

      // 5. Goodbye
      {
        intent: 'goodbye',
        patterns: [
          /\b(bye|goodbye|see\s+you|exit|quit|stop\s+talking|namaste\s+alvida)\b/i,
          /(अलविदा|बाय|शुभकामनाएं)/,
        ],
        generateResponse: (_, input) => {
          const isHindi = /[\u0900-\u097F]/.test(input);
          return isHindi
            ? 'अलविदा! आपकी फसल समृद्ध रहे। जब भी बात करनी हो, स्टार्ट लिसनिंग पर क्लिक करें।'
            : 'Goodbye! May your harvest be bountiful. Click Start Listening whenever you wish to speak again.';
        },
        repeatable: true,
      },

      // 6. Optional Domain Preview (Farm Status)
      {
        intent: 'farm_status',
        patterns: [
          /\b(farm\s+status|field\s+status|farm\s+overview|farm\s+info|soil\s*(moisture|health)|crop\s+status|temperature|check\s+sensor)\b/i,
          /(खेत\s*की\s*(स्थिति|जानकारी|हालत|रिपोर्ट)|खेत\s*का\s*(हाल|हालचाल)|मिट्टी|फसल\s*की\s*स्थिति)/,
        ],
        generateResponse: (_, input) => {
          const isHindi = /[\u0900-\u097F]/.test(input);
          return isHindi
            ? '[डेमो टेलीमेट्री] मिट्टी की नमी: 48.2% (अनुकूल)। मिट्टी का तापमान: 24.5°C। पानी का टैंक: 82%। सभी 3 सेंसर ऑनलाइन हैं।'
            : '[DEMO TELEMETRY] Soil Moisture: 48.2% (Optimal). Soil Temp: 24.5°C. Water Tank: 82%. All 3 simulated sensors are online.';
        },
        repeatable: true,
      },

      // 7. Pump Status
      {
        intent: 'farm_status',
        patterns: [
          /\b(is\s+(the\s+)?pump\s+(running|on|off|active)|pump\s+status)\b/i,
          /(पंप\s*(चालू\s*है\s*या\s*बंद|चल\s*रहा\s*है|की\s*स्थिति)|क्या\s*पंप\s*चालू\s*है)/,
        ],
        generateResponse: (_, input) => {
          const isHindi = /[\u0900-\u097F]/.test(input);
          return isHindi
            ? 'DEMO-ZONE-001 के लिए पानी का पंप वर्तमान में बंद (OFF) है। (सिम्युलेटेड मोड)'
            : 'Water pump for DEMO-ZONE-001 is currently STOPPED (OFF). (Simulated mode)';
        },
        repeatable: true,
      },

      // 8. Pump Shutdown
      {
        intent: 'farm_status',
        patterns: [
          /\b(turn\s*off|shut\s*off|stop)\s+(the\s+)?(pump|irrigation|motor)\b/i,
          /(पंप|सिंचाई|पानी|मोटर)\s*(बंद\s*कर\s*दो|बंद\s*करो|रोको|ऑफ\s*करो)/,
        ],
        generateResponse: (_, input) => {
          const isHindi = /[\u0900-\u097F]/.test(input);
          return isHindi
            ? 'पानी का पंप तुरंत बंद कर दिया गया है। (सिम्युलेटेड मोड)'
            : 'Water pump has been shut off immediately. (Simulated mode)';
        },
        repeatable: true,
      },

      // 9. Pump Activation Request
      {
        intent: 'irrigation_inquiry',
        patterns: [
          /\b(turn\s*on|start|activate)\s+(the\s+)?(pump|irrigation|motor)\b/i,
          /(पंप|पानी\s*का\s*पंप|सिंचाई|मोटर)\s*(चालू\s*कर\s*दो|चालू\s*करो|ऑन\s*कर\s*दो|शुरू\s*करो)/,
        ],
        generateResponse: (_, input) => {
          const isHindi = /[\u0900-\u097F]/.test(input);
          return isHindi
            ? 'पंप चालू करने की अनुमति दें? क्या आप DEMO-ZONE-001 में पानी का पंप चालू करना चाहते हैं? कृपया नीचे दिए गए बटन से पुष्टि करें।'
            : 'Permission required. Do you want to turn on the water pump for DEMO-ZONE-001? Please confirm using the buttons below.';
        },
        repeatable: false,
      },
    ];
  }

  /**
   * Processes raw user input into an intent and deterministic response.
   * Returns null if input is empty or whitespace.
   */
  public processInput(rawInput: string): EngineResponse | null {
    const trimmed = rawInput.trim();
    if (!trimmed) {
      return null;
    }

    const isHindi = /[\u0900-\u097F]/.test(trimmed);

    // Match against configured intent rules
    for (const rule of this.rules) {
      for (const pattern of rule.patterns) {
        if (pattern.test(trimmed)) {
          const text = rule.generateResponse(this, trimmed);
          if (rule.repeatable) {
            this.lastAgentResponse = text;
          }
          return {
            intent: rule.intent,
            text,
            confidence: 1.0,
            repeatable: rule.repeatable,
          };
        }
      }
    }

    // Unknown Fallback
    const fallbackText = isHindi
      ? "मुझे इस डेमो में यह समझ नहीं आया। 'नमस्ते', 'आप कौन हैं?', 'खेत की स्थिति', या 'अलविदा' पूछने का प्रयास करें।"
      : "I didn't quite catch that in this demo. Try asking: 'Hello', 'Who are you?', 'What can you do?', or 'Goodbye'.";
    this.lastAgentResponse = fallbackText;

    return {
      intent: 'unknown',
      text: fallbackText,
      confidence: 0.2,
      repeatable: true,
    };
  }

  public getLastResponse(): string | null {
    return this.lastAgentResponse;
  }

  public setLastResponse(response: string | null): void {
    this.lastAgentResponse = response;
  }

  public clearHistory(): void {
    this.lastAgentResponse = null;
  }
}
