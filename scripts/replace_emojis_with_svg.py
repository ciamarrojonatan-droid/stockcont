"""
Replace all emojis in stockcont/README.md with professional SVGs.
"""
import re
import sys
from pathlib import Path

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

STOCKCONT_README = Path("README.md")

REPLACEMENTS = {
    # Headers
    "## 📑 Sumário Executivo": '## <img src="docs/icons/book.svg" width="20" height="20" /> Sumário Executivo',
    "## 🔭 Visão Geral do Sistema": '## <img src="docs/icons/globe.svg" width="20" height="20" /> Visão Geral do Sistema',
    "## 🎬 Visão Geral do Sistema & Propósito Industrial": '## <img src="docs/icons/film.svg" width="20" height="20" /> Visão Geral do Sistema & Propósito Industrial',
    "## 🏛️ Arquitetura de Alto Nível & Topologia da Esteira": '## <img src="docs/icons/layers.svg" width="20" height="20" /> Arquitetura de Alto Nível & Topologia da Esteira',
    "## 🏛 Arquitetura de Alto Nível & Topologia da Esteira": '## <img src="docs/icons/layers.svg" width="20" height="20" /> Arquitetura de Alto Nível & Topologia da Esteira',
    "## 🧠 Mapa Mental da Máquina de Retenção & Monetização": '## <img src="docs/icons/mindmap.svg" width="20" height="20" /> Mapa Mental da Máquina de Retenção & Monetização',
    "## <img src=\"docs/icons/gear.svg\" width=\"20\" height=\"20\" /> Detalhamento Técnico das Fases do Pipeline": '## <img src="docs/icons/gear.svg" width="20" height="20" /> Detalhamento Técnico das Fases do Pipeline',
    "## ⚙️ Detalhamento Técnico das Fases do Pipeline": '## <img src="docs/icons/gear.svg" width="20" height="20" /> Detalhamento Técnico das Fases do Pipeline',
    "## ⚙ Detalhamento Técnico das Fases do Pipeline": '## <img src="docs/icons/gear.svg" width="20" height="20" /> Detalhamento Técnico das Fases do Pipeline',
    "## 🖥️ Dashboard Web SPA Local (iOS 27 Liquid Glass)": '## <img src="docs/icons/desktop.svg" width="20" height="20" /> Dashboard Web SPA Local (iOS 27 Liquid Glass)',
    "## 🖥 Dashboard Web SPA Local (iOS 27 Liquid Glass)": '## <img src="docs/icons/desktop.svg" width="20" height="20" /> Dashboard Web SPA Local (iOS 27 Liquid Glass)',
    "## 🤖 Daemon Autônomo 24/7 & Watchdog de Produção": '## <img src="docs/icons/robot.svg" width="20" height="20" /> Daemon Autônomo 24/7 & Watchdog de Produção',
    "## 📄 Contratos de Dados (Data Schemas Tipados)": '## <img src="docs/icons/file-text.svg" width="20" height="20" /> Contratos de Dados (Data Schemas Tipados)',
    "## 📄 Contratos de Dados (Data Schemas v3.0)": '## <img src="docs/icons/file-text.svg" width="20" height="20" /> Contratos de Dados (Data Schemas v3.0)',
    "## 🛠️ Instalação, Configuração & Execução CLI": '## <img src="docs/icons/tool.svg" width="20" height="20" /> Instalação, Configuração & Execução CLI',
    "## 🛠 Instalação, Configuração & Execução CLI": '## <img src="docs/icons/tool.svg" width="20" height="20" /> Instalação, Configuração & Execução CLI',
    "## 🛠️ Instalação, Configuração & Execução": '## <img src="docs/icons/tool.svg" width="20" height="20" /> Instalação, Configuração & Execução',
    "## 🛠 Instalação, Configuração & Execução": '## <img src="docs/icons/tool.svg" width="20" height="20" /> Instalação, Configuração & Execução',
    "## 🛡️ Resiliência Operacional & Decisões Arquiteturais (ADRs)": '## <img src="docs/icons/shield.svg" width="20" height="20" /> Resiliência Operacional & Decisões Arquiteturais (ADRs)',
    "## 🛡 Resiliência Operacional & Decisões Arquiteturais (ADRs)": '## <img src="docs/icons/shield.svg" width="20" height="20" /> Resiliência Operacional & Decisões Arquiteturais (ADRs)',
    "## 🛡️ Resiliência Operacional & Decisões de Engenharia (ADRs)": '## <img src="docs/icons/shield.svg" width="20" height="20" /> Resiliência Operacional & Decisões de Engenharia (ADRs)',
    "## 🛡 Resiliência Operacional & Decisões de Engenharia (ADRs)": '## <img src="docs/icons/shield.svg" width="20" height="20" /> Resiliência Operacional & Decisões de Engenharia (ADRs)',
    "## 🚀 Orquestrador Mestre CLI (`main.py`) & Scripts de Execução": '## <img src="docs/icons/terminal.svg" width="20" height="20" /> Orquestrador Mestre CLI (`main.py`) & Scripts de Execução',
    "## 📁 Estrutura do Repositório & Gestão de Dados": '## <img src="docs/icons/folder.svg" width="20" height="20" /> Estrutura do Repositório & Gestão de Dados',
    "## 📊 Matriz Estratégica Multi-Agência & Proteção Anti-Ban Alamy": '## <img src="docs/icons/shield-check.svg" width="20" height="20" /> Matriz Estratégica Multi-Agência & Proteção Anti-Ban Alamy',
    
    # Sub-headers
    "### 🎬 Pipeline de Vídeo Cinematográfico (Fases 1 a 5 de Vídeo)": '### <img src="docs/icons/film.svg" width="18" height="18" /> Pipeline de Vídeo Cinematográfico (Fases 1 a 5 de Vídeo)',
    "### 🔬 Módulo QC: Curadoria Multimodal & Prevenção OOM": '### <img src="docs/icons/microscope.svg" width="18" height="18" /> Módulo QC: Curadoria Multimodal & Prevenção OOM',
    "### ☁️ O Cofre Cloud (Google Drive + Auto-Purga Inteligente de SSD)": '### <img src="docs/icons/cloud.svg" width="18" height="18" /> O Cofre Cloud (Google Drive + Auto-Purga Inteligente de SSD)',
    "### ☁ O Cofre Cloud (Google Drive + Auto-Purga Inteligente de SSD)": '### <img src="docs/icons/cloud.svg" width="18" height="18" /> O Cofre Cloud (Google Drive + Auto-Purga Inteligente de SSD)',
    "### 🤖 Motor Autônomo 24/7 (Daemon Supervisor & Watchdog Windows)": '### <img src="docs/icons/robot.svg" width="18" height="18" /> Motor Autônomo 24/7 (Daemon Supervisor & Watchdog Windows)',
    "> ### ⚠️ ALERTA MANDATÓRIO DE COMPLIANCE - ALAMY (ADR-05)": '> ### <img src="docs/icons/alert.svg" width="18" height="18" /> ALERTA MANDATÓRIO DE COMPLIANCE - ALAMY (ADR-05)',
    "> ### ⚠ ALERTA MANDATÓRIO DE COMPLIANCE - ALAMY (ADR-05)": '> ### <img src="docs/icons/alert.svg" width="18" height="18" /> ALERTA MANDATÓRIO DE COMPLIANCE - ALAMY (ADR-05)',

    # In-body inline icons
    '"⚡ Produção 24/7"': '"<img src=\\"docs/icons/bolt.svg\\" width=\\"14\\" height=\\"14\\" /> Produção 24/7"',
    '🟢 Rodando 24/7': '<img src="docs/icons/status-green.svg" width="12" height="12" /> Rodando 24/7',
    '🔴 Parado': '<img src="docs/icons/status-red.svg" width="12" height="12" /> Parado',
    '🟢 Instant Green Dollar Sign': '<img src="docs/icons/status-green.svg" width="12" height="12" /> Instant Green Dollar Sign',
    '⚡ Mineração Autônoma': '<img src="docs/icons/bolt.svg" width="14" height="14" /> Mineração Autônoma',
    '🎯 **Blue Ocean**': '<img src="docs/icons/target.svg" width="14" height="14" /> **Blue Ocean**',
    '🟡 **Competição Moderada**': '<img src="docs/icons/status-yellow.svg" width="12" height="12" /> **Competição Moderada**',
    '🔴 **Red Ocean**': '<img src="docs/icons/status-red.svg" width="12" height="12" /> **Red Ocean**',
    '| ✅ Aceito': '| <img src="docs/icons/check.svg" width="14" height="14" /> Aceito',
    '| ⛔ **TERMINANTEMENTE PROIBIDO PARA IA**': '| <img src="docs/icons/ban.svg" width="14" height="14" /> **TERMINANTEMENTE PROIBIDO PARA IA**',
    '| ⛔ PROIBIDO': '| <img src="docs/icons/ban.svg" width="14" height="14" /> PROIBIDO',
    '| 🛡️ **BLOQUEIO ATIVO': '| <img src="docs/icons/shield.svg" width="14" height="14" /> **BLOQUEIO ATIVO',
    '| 🛡 **BLOQUEIO ATIVO': '| <img src="docs/icons/shield.svg" width="14" height="14" /> **BLOQUEIO ATIVO',
    '🛡️ Resiliência': '<img src="docs/icons/shield.svg" width="16" height="16" /> Resiliência',
    '🛡 Resiliência': '<img src="docs/icons/shield.svg" width="16" height="16" /> Resiliência',
}

def clean_file(path: Path):
    if not path.exists():
        print(f"Skipping non-existent: {path}")
        return
    content = path.read_text(encoding="utf-8")
    for src, dst in REPLACEMENTS.items():
        content = content.replace(src, dst)
    
    # Generic emoji cleaner for any remaining emoji characters
    emoji_pattern = re.compile(
        r"[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf\u2300-\u23ff\u2b50-\u2b55]"
    )
    # Check if any remaining emojis
    matches = emoji_pattern.findall(content)
    if matches:
        print(f"Remaining emojis in {path.name}: {set(matches)}")
        # Clean specific stragglers if any
        for em in set(matches):
            if em == "🚀":
                content = content.replace(em, '<img src="docs/icons/terminal.svg" width="16" height="16" />')
            elif em == "🎬":
                content = content.replace(em, '<img src="docs/icons/film.svg" width="16" height="16" />')
            elif em in ["✅", "✔"]:
                content = content.replace(em, '<img src="docs/icons/check.svg" width="14" height="14" />')
            elif em in ["⛔", "❌"]:
                content = content.replace(em, '<img src="docs/icons/ban.svg" width="14" height="14" />')
            elif em in ["⚠️", "⚠"]:
                content = content.replace(em, '<img src="docs/icons/alert.svg" width="15" height="15" />')
            elif em == "🟢":
                content = content.replace(em, '<img src="docs/icons/status-green.svg" width="12" height="12" />')
            elif em == "🔴":
                content = content.replace(em, '<img src="docs/icons/status-red.svg" width="12" height="12" />')
            elif em == "🟡":
                content = content.replace(em, '<img src="docs/icons/status-yellow.svg" width="12" height="12" />')
            elif em == "⚡":
                content = content.replace(em, '<img src="docs/icons/bolt.svg" width="14" height="14" />')
            elif em == "🛡":
                content = content.replace(em, '<img src="docs/icons/shield.svg" width="16" height="16" />')
            else:
                # remove any remaining miscellaneous emoji
                content = content.replace(em, "")
    else:
        print(f"No remaining emojis in {path.name}!")
        
    path.write_text(content, encoding="utf-8")
    print(f"Successfully processed {path.name}")

if __name__ == "__main__":
    clean_file(STOCKCONT_README)
