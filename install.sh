#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}"
echo "  _                    _ _           "
echo " | |    ___   ___ __ _| (_)___  __ _ "
echo " | |   / _ \ / __/ _\` | | / __|/ _\` |"
echo " | |__| (_) | (_| (_| | | \__ \ (_| |"
echo " |_____\___/ \___\__,_|_|_|___/\__,_|"
echo ""
echo " AI that lives in the real world."
echo -e "${NC}"
echo "=========================================="
echo ""

# --- Check prerequisites ---
echo -e "${BOLD}Checking requirements...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker not found. Install: https://docs.docker.com/get-docker/${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} $(docker --version)"

if ! docker compose version &> /dev/null; then
    echo -e "${RED}Docker Compose not found. Install docker-compose-plugin.${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} $(docker compose version)"

# --- Detect GPU ---
GPU_DETECTED=false
if command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | head -1)
    if [ -n "$GPU_NAME" ]; then
        GPU_DETECTED=true
        echo -e "  ${GREEN}✓${NC} NVIDIA GPU: ${GPU_NAME} (${GPU_MEM})"
    fi
fi

if [ "$GPU_DETECTED" = false ]; then
    echo -e "  ${YELLOW}!${NC} No NVIDIA GPU detected (CPU mode available)"
fi

# --- Detect Ollama ---
OLLAMA_DETECTED=false
OLLAMA_URL="http://localhost:11434"
if curl -s "${OLLAMA_URL}/api/tags" &> /dev/null; then
    OLLAMA_DETECTED=true
    OLLAMA_MODELS=$(curl -s "${OLLAMA_URL}/api/tags" | python3 -c "
import sys, json
data = json.load(sys.stdin)
models = data.get('models', [])
for m in models[:5]:
    size = m.get('size', 0) / (1024**3)
    print(f\"    - {m['name']} ({size:.1f}GB)\")
" 2>/dev/null || echo "    (could not list models)")
    echo -e "  ${GREEN}✓${NC} Ollama found at ${OLLAMA_URL}"
    if [ -n "$OLLAMA_MODELS" ]; then
        echo -e "  Models available:"
        echo "$OLLAMA_MODELS"
    fi
fi

echo ""

# --- Network scan (quick) ---
echo -e "${BOLD}Scanning your network...${NC}"
SUBNET=$(ip route | grep 'src' | head -1 | awk '{print $1}')
if [ -n "$SUBNET" ]; then
    # Quick ping scan + port check for common services
    FOUND_DEVICES=()

    # Check for MQTT broker (port 1883)
    for ip in $(seq 1 254); do
        BASE=$(echo $SUBNET | sed 's|/.*||' | sed 's|\.[0-9]*$||')
        HOST="${BASE}.${ip}"
        if timeout 0.1 bash -c "echo >/dev/tcp/${HOST}/1883" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} MQTT Broker (${HOST}:1883)"
            FOUND_MQTT=$HOST
            break
        fi
    done 2>/dev/null || true

    # Check for common ports on local subnet
    for port_name in "8123:Home Assistant" "80:Pi-hole/Router" "5353:mDNS"; do
        PORT=$(echo $port_name | cut -d: -f1)
        NAME=$(echo $port_name | cut -d: -f2)
    done
else
    echo -e "  ${YELLOW}!${NC} Could not determine network subnet"
fi
echo ""

# --- LLM Backend selection ---
echo -e "${BOLD}LLM Backend:${NC}"
echo ""
if [ "$OLLAMA_DETECTED" = true ]; then
    echo "  [1] Ollama (detected on this machine) [recommended]"
else
    echo "  [1] Ollama (not detected — install from ollama.com)"
fi
echo "  [2] Cloud API (DeepSeek \$0.14/M tok, Groq free, Claude, OpenAI)"
if [ "$GPU_DETECTED" = true ]; then
    echo "  [3] Built-in vLLM (uses your ${GPU_NAME})"
fi
echo "  [4] Custom URL (existing OpenAI-compatible server)"
echo ""
read -p "  Selection [1]: " LLM_CHOICE
LLM_CHOICE=${LLM_CHOICE:-1}

LLM_BACKEND="ollama"
case $LLM_CHOICE in
    1)
        LLM_BACKEND="ollama"
        if [ "$OLLAMA_DETECTED" = true ]; then
            read -p "  Ollama model to use [qwen2.5:3b]: " OLLAMA_MODEL
            OLLAMA_MODEL=${OLLAMA_MODEL:-qwen2.5:3b}
            # Pull model if not available
            if ! curl -s "${OLLAMA_URL}/api/tags" | grep -q "\"$OLLAMA_MODEL\""; then
                echo -e "  Pulling ${OLLAMA_MODEL}..."
                ollama pull "$OLLAMA_MODEL"
            fi
        else
            echo -e "  ${YELLOW}Install Ollama first: curl -fsSL https://ollama.com/install.sh | sh${NC}"
            OLLAMA_MODEL="qwen2.5:3b"
        fi
        ;;
    2)
        LLM_BACKEND="cloud"
        echo ""
        echo "  Cloud providers:"
        echo "    [a] DeepSeek (\$0.14/M tokens)"
        echo "    [b] Groq (free tier)"
        echo "    [c] Claude (Anthropic)"
        echo "    [d] OpenAI"
        read -p "  Provider [a]: " CLOUD_CHOICE
        CLOUD_CHOICE=${CLOUD_CHOICE:-a}
        case $CLOUD_CHOICE in
            a) LLM_CLOUD_PROVIDER="deepseek"; LLM_CLOUD_MODEL="deepseek-chat" ;;
            b) LLM_CLOUD_PROVIDER="groq"; LLM_CLOUD_MODEL="llama-3.1-8b-instant" ;;
            c) LLM_CLOUD_PROVIDER="claude"; LLM_CLOUD_MODEL="claude-sonnet-4-20250514" ;;
            d) LLM_CLOUD_PROVIDER="openai"; LLM_CLOUD_MODEL="gpt-4o-mini" ;;
        esac
        read -p "  API Key: " LLM_CLOUD_API_KEY
        ;;
    3)
        LLM_BACKEND="vllm"
        read -p "  Model [Qwen/Qwen2.5-7B-Instruct-AWQ]: " VLLM_MODEL
        VLLM_MODEL=${VLLM_MODEL:-Qwen/Qwen2.5-7B-Instruct-AWQ}
        ;;
    4)
        LLM_BACKEND="custom"
        read -p "  API URL: " LLM_CUSTOM_URL
        read -p "  API Key (empty if none): " LLM_CUSTOM_API_KEY
        ;;
esac

echo ""

# --- Optional features ---
echo -e "${BOLD}Optional features:${NC}"
echo ""

read -p "  Enable voice (Whisper + TTS)? [Y/n]: " VOICE_ENABLED
VOICE_ENABLED=${VOICE_ENABLED:-Y}

read -p "  Enable Telegram bot? [y/N]: " TELEGRAM_ENABLED
TELEGRAM_ENABLED=${TELEGRAM_ENABLED:-N}
if [[ "$TELEGRAM_ENABLED" =~ ^[Yy] ]]; then
    read -p "    Bot token: " TELEGRAM_BOT_TOKEN
    read -p "    Allowed user IDs (comma-separated): " TELEGRAM_ALLOWED_USERS
fi

read -p "  Enable home automation (MQTT)? [y/N]: " HOME_ENABLED
HOME_ENABLED=${HOME_ENABLED:-N}

echo ""

# --- Language ---
read -p "  Language / Idioma [es/en]: " LANG_CHOICE
LANG_CHOICE=${LANG_CHOICE:-es}

echo ""

# --- Generate .env ---
echo -e "${BOLD}Generating configuration...${NC}"

cp .env.example .env

sed -i "s|^LLM_BACKEND=.*|LLM_BACKEND=${LLM_BACKEND}|" .env
sed -i "s|^LOCALISA_LANG=.*|LOCALISA_LANG=${LANG_CHOICE}|" .env

case $LLM_BACKEND in
    ollama)
        sed -i "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=${OLLAMA_MODEL}|" .env
        ;;
    cloud)
        sed -i "s|^LLM_CLOUD_PROVIDER=.*|LLM_CLOUD_PROVIDER=${LLM_CLOUD_PROVIDER}|" .env
        sed -i "s|^LLM_CLOUD_API_KEY=.*|LLM_CLOUD_API_KEY=${LLM_CLOUD_API_KEY}|" .env
        sed -i "s|^LLM_CLOUD_MODEL=.*|LLM_CLOUD_MODEL=${LLM_CLOUD_MODEL}|" .env
        ;;
    vllm)
        sed -i "s|^VLLM_MODEL=.*|VLLM_MODEL=${VLLM_MODEL}|" .env
        ;;
    custom)
        sed -i "s|^LLM_CUSTOM_URL=.*|LLM_CUSTOM_URL=${LLM_CUSTOM_URL}|" .env
        sed -i "s|^LLM_CUSTOM_API_KEY=.*|LLM_CUSTOM_API_KEY=${LLM_CUSTOM_API_KEY}|" .env
        ;;
esac

if [[ "$TELEGRAM_ENABLED" =~ ^[Yy] ]]; then
    sed -i "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}|" .env
    sed -i "s|^TELEGRAM_ALLOWED_USERS=.*|TELEGRAM_ALLOWED_USERS=${TELEGRAM_ALLOWED_USERS}|" .env
fi

echo -e "  ${GREEN}✓${NC} .env generated"

# --- Build profiles ---
PROFILES=""
if [[ "$VOICE_ENABLED" =~ ^[Yy] ]]; then
    PROFILES="$PROFILES --profile voice"
fi
if [[ "$TELEGRAM_ENABLED" =~ ^[Yy] ]]; then
    PROFILES="$PROFILES --profile telegram"
fi
if [[ "$HOME_ENABLED" =~ ^[Yy] ]]; then
    PROFILES="$PROFILES --profile home"
fi

# --- Create data dirs ---
mkdir -p data/{chromadb,redis,documents,models,voice,vault,mosquitto}

echo ""
echo -e "${BOLD}Building and starting services...${NC}"
echo ""

# --- Build and start ---
docker compose $PROFILES build
docker compose $PROFILES up -d

echo ""

# --- Wait for health ---
echo -e "${BOLD}Waiting for services...${NC}"
for i in $(seq 1 30); do
    if curl -s http://localhost:5002/api/health > /dev/null 2>&1; then
        break
    fi
    sleep 2
done

echo ""
echo -e "${GREEN}${BOLD}=========================================="
echo ""
echo "  Localisa is ready!"
echo ""
echo "  Web UI:   http://localhost:${WEB_PORT:-8080}"
if [[ "$TELEGRAM_ENABLED" =~ ^[Yy] ]]; then
    echo "  Telegram: your bot is active"
fi
echo ""
echo "  Try: \"What can you do?\""
echo "  Try: Upload a PDF and ask about it!"
echo ""
echo "==========================================${NC}"
