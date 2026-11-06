#!/bin/bash

#Aquivo Shell Script para reproduzir o áudio de cada figura.
# Uso: toca_som.sh <circulo|hexagono|triangulo> [diretorio_dos_audios]

#Códigos de saída: 

# 0: ok  
# 1: arquivo não encontrado  
# 2: argumento inválido
# 3: nenhum player disponível  
# 4 falha ao reproduzir
#-------------------------------------------------------------------------#

set -u
set -o pipefail

QUAL="${1:-}"
DIR="${2:-$(dirname "$(readlink -f "$0")")/../audio}"

case "$QUAL" in
  circulo)   ARQ="1_circulo.mp3" ;;
  hexagono)  ARQ="2_hexagono.mp3" ;;
  triangulo) ARQ="3_triangulo.mp3" ;;
  *) echo "Uso: $0 <circulo|hexagono|triangulo> [diretorio]" >&2; exit 2 ;;
esac

CAMINHO="$DIR/$ARQ"
if [ ! -f "$CAMINHO" ]; then
  echo "Arquivo não encontrado: $CAMINHO" >&2
  exit 1
fi

if command -v ffmpeg >/dev/null 2>&1 && command -v paplay >/dev/null 2>&1; then
  ffmpeg -loglevel quiet -i "$CAMINHO" -f wav - | paplay || exit 4
elif command -v ffplay >/dev/null 2>&1; then
  ffplay -nodisp -autoexit -loglevel quiet "$CAMINHO" || exit 4
else
  echo "Nenhum player disponível (ffmpeg+paplay ou ffplay)." >&2
  exit 3
fi
