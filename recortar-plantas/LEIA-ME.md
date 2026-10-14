# Skill `recortar-plantas` (Claude Code)

## O que faz
Recorta a planta humanizada de cada pavimento (tipo, rooftop, garden, mezanino...) em **uma imagem PNG por
unidade**: fundo branco, sem girar, na resolução original, com varanda/terraço/garden da unidade, sem os textos de
área (m²) e mantendo a numeração. Aceita PNG/JPG e PDF. Opcional: junta pavimento + mezanino numa imagem só (para
sistemas que aceitam uma planta por unidade, como o SpotSys).

## Como instalar
1. Copie a pasta `recortar-plantas` (inteira) para `%USERPROFILE%\.claude\skills\`
   (fica `%USERPROFILE%\.claude\skills\recortar-plantas\SKILL.md`).
2. Reinicie o Claude Code.
3. Use com `/recortar-plantas` ou peça "recorta as unidades desta planta" indicando a pasta do empreendimento.

## Requisitos
- Python 3 com: `pip install pillow opencv-python numpy pymupdf pytesseract`
- Tesseract OCR instalado em `C:\Program Files\Tesseract-OCR` (instalador para Windows: UB Mannheim).
- Só para ampliar planta pequena com IA (raro): `pip install torch` + o modelo abaixo.

## Modelo de IA (opcional, 64 MB, não vem no pacote)
Baixe `https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth` e salve em
`%USERPROFILE%\.claude\skills\recortar-plantas\modelos\RealESRGAN_x4plus.pth`.
