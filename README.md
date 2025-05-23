# Ninja Extrator 7000

Um conjunto de ferramentas poderosas para extrair vídeos de plataformas educacionais com autenticação, especialmente do Ulife/Ebradi.

## Funcionalidades

- **TS Downloader**: Baixa vídeos no formato .ts e os converte para MP4
- **Ulife Extractor**: Navegação assistida com Selenium para capturar cookies e URLs necessárias para download

## Características do TS Downloader

- Baixa o ffmpeg localmente no diretório do projeto se necessário
- Implementa múltiplos métodos de conversão e remuxagem
- Detecção inteligente de formatos de arquivo
- Mecanismos de recuperação em caso de falha

## Como usar

### TS Downloader

```bash
python ts_downloader.py https://url-do-video/segmento.ts
```

Opções:
- `-o, --output`: Nome do arquivo de saída
- `-s, --start`: Número do segmento inicial (padrão: 0)
- `-m, --max`: Número máximo de segmentos (padrão: 500)
- `--skip-cleanup`: Não apagar arquivos temporários
- `--ffmpeg-path`: Caminho para o executável do ffmpeg

### Ulife Extractor

```bash
python ulife_extractor.py
```

Este script abrirá um navegador automatizado para você fazer login manualmente. Depois do login, navegue até a página do vídeo desejado e o script capturará as informações necessárias para download.

## Requisitos

- Python 3.6+
- FFmpeg (instalado automaticamente se não encontrado)
- Bibliotecas: requests, selenium (para o ulife_extractor)

## Instalação

```bash
# Clone o repositório
git clone https://github.com/caiorcastro/Ninja-Extrator-7000.git
cd Ninja-Extrator-7000

# Instale as dependências
pip install -r requirements.txt
```

## Licença

Este projeto é distribuído sob a licença MIT.

## Aviso Legal

Esta ferramenta foi desenvolvida para uso pessoal e educacional. O uso desta ferramenta para baixar conteúdo protegido por direitos autorais sem permissão pode violar os termos de serviço das plataformas e leis de direitos autorais. Use por sua conta e risco. 