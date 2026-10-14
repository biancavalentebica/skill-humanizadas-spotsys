# rodar.sh config.json : recorta, corrige via OCR (ate 3x) e limpa bordas
K="$(cd "$(dirname "$0")" && pwd)"
python "$K/recortar.py" "$1" | tail -1
for i in 1 2 3; do ids=$(python "$K/corrigir.py" "$1"); [ -z "$ids" ] && break; echo "corrigindo $ids"; eval python "$K/recortar.py" "$1" $ids | tail -1; done
python "$K/limpar_bordas.py" "$1"
