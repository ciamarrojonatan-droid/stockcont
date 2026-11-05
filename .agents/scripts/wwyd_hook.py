#!/usr/bin/env python3
"""PreInvocation hook: Auto-detects strategic decision triggers and activates 'O que você faria?'.

Contract: PreInvocation → input has invocationNum, messages/user input.
          Output: { "injectSteps": [...] } or {}
"""
import json
import sys

TRIGGERS = [
    "o que voce faria",
    "o que você faria",
    "o que vc faria",
    "o que faria",
    "what would you do",
    "qual sua opiniao",
    "qual sua opinião",
    "o que acha",
    "vale a pena",
    "devo fazer",
    "qual caminho",
    "wwyd",
]

ADVISOR_INJECTION = (
    "🎯 [PROTOCOLO ATIVO: O QUE VOCÊ FARIA?]\n"
    "O usuário está solicitando aconselhamento estratégico de alto nível ou tomada de decisão.\n"
    "Assuma a postura de Sócio Sênior Pragmático com Skin in the Game:\n"
    "1. Diagnóstico Cru (Sem floreios ou bajulação)\n"
    "2. O Que Eu Faria (A Escolha Definitiva e fundamentada, sem 'depende')\n"
    "3. O Que Eu NÃO Faria de Jeito Nenhum (Anti-armadilhas)\n"
    "4. O Playbook das Primeiras 48 Horas (The Golden Slice)\n"
    "5. O Gatilho de Corte / Kill-Switch (Métrica objetiva de decisão)"
)


def main() -> None:
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({}))
            return
        payload = json.loads(raw_input)
    except Exception:
        print(json.dumps({}))
        return

    # Check for trigger phrases in payload or recent messages
    should_trigger = False
    payload_str = json.dumps(payload).lower()
    for trigger in TRIGGERS:
        if trigger in payload_str:
            should_trigger = True
            break

    if should_trigger:
        output = {
            "injectSteps": [
                {
                    "type": "ephemeralMessage",
                    "content": ADVISOR_INJECTION,
                }
            ]
        }
        print(json.dumps(output))
    else:
        print(json.dumps({}))


if __name__ == "__main__":
    main()
