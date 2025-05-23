#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TS Downloader - Baixador de vídeos em segmentos .ts
Este script baixa sequências de arquivos .ts e os combina em um único arquivo MP4
"""

import os
import re
import sys
import time
import shutil
import argparse
import requests
import subprocess
from pathlib import Path
from urllib.parse import urlparse

# Configurações
TEMP_DIR = Path("./temp_segments")
OUTPUT_DIR = Path("./videos")
MAX_RETRIES = 3
TIMEOUT = 30
SLEEP_BETWEEN_REQUESTS = 0.2

def ensure_dirs():
    """Garante que os diretórios necessários existem"""
    TEMP_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    return TEMP_DIR, OUTPUT_DIR

def download_segment(url, output_path, session=None, retries=0):
    """
    Baixa um segmento individual de vídeo
    
    Args:
        url: URL do segmento
        output_path: Caminho para salvar o segmento
        session: Sessão de requests (opcional)
        retries: Número de tentativas já realizadas
        
    Returns:
        bool: True se o download foi bem-sucedido, False caso contrário
    """
    if retries > MAX_RETRIES:
        print(f"Erro: Número máximo de tentativas excedido para {url}")
        return False
    
    try:
        if session is None:
            session = requests
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": f"https://{urlparse(url).netloc}/"
        }
        
        response = session.get(url, headers=headers, timeout=TIMEOUT)
        
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True
        elif response.status_code == 403 or response.status_code == 404:
            # Se for 403 (Forbidden) ou 404 (Not Found), provavelmente chegamos ao fim dos segmentos
            print(f"Segmento não disponível (status {response.status_code}): {url}")
            return False
        else:
            print(f"Erro ao baixar segmento {url} - Status: {response.status_code}")
            time.sleep(1 + retries)  # Espera um pouco mais a cada retry
            return download_segment(url, output_path, session, retries + 1)
            
    except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
        print(f"Erro de conexão: {str(e)}")
        time.sleep(1 + retries)  # Espera um pouco mais a cada retry
        return download_segment(url, output_path, session, retries + 1)
    except Exception as e:
        print(f"Erro desconhecido: {str(e)}")
        return False

def download_all_segments(base_url, output_name, start_segment=0, max_segments=1000):
    """
    Baixa todos os segmentos de vídeo em sequência
    
    Args:
        base_url: URL base dos segmentos (sem o número)
        output_name: Nome do arquivo de saída
        start_segment: Número do segmento inicial
        max_segments: Número máximo de segmentos a tentar
        
    Returns:
        list: Lista de caminhos dos segmentos baixados
    """
    # Extrair o diretório base e o padrão de nome do arquivo
    url_parts = urlparse(base_url)
    url_path = url_parts.path
    
    # Verificar se é uma URL da Ebradi
    is_ebradi = "ebradi" in url_path.lower()
    
    # Determinar o formato do nome do segmento
    if "quality_" in url_path:
        # Formato: quality_720.ts, quality_720_001.ts, etc.
        base_name = re.sub(r'_\d+\.ts$', '', url_path.split('/')[-1])
        ext = ".ts"
        segment_format = "sequential"  # Formato sequencial (000, 001, 002...)
    else:
        # Outro formato, assumir padrão genérico
        base_name = url_path.split('/')[-1].split('.')[0]
        ext = ".ts"
        segment_format = "sequential"
    
    # Criar sessão para reutilizar conexões
    session = requests.Session()
    
    temp_dir, output_dir = ensure_dirs()
    segment_paths = []
    
    print(f"\nIniciando download dos segmentos de {base_url}")
    print(f"Formato detectado: {segment_format}")
    
    if is_ebradi:
        print(f"Detectado vídeo da Ebradi. Verificando formatos específicos.")
    
    # Baixar segmentos em sequência
    segment_count = 0
    consecutive_failures = 0
    i = start_segment
    
    # Primeiro, tenta baixar o segmento inicial
    print(f"Baixando segmento {i}: {base_url}")
    segment_filename = f"segment_{i:03d}{ext}"
    segment_path = temp_dir / segment_filename
    
    if download_segment(base_url, segment_path, session):
        segment_paths.append(segment_path)
        segment_count += 1
        
        # Para vídeos da Ebradi, se tivermos apenas um segmento grande, pode ser o vídeo completo
        if is_ebradi:
            filesize = segment_path.stat().st_size / (1024 * 1024)  # MB
            print(f"Tamanho do segmento: {filesize:.2f} MB")
            
            if filesize > 50:  # Se for maior que 50MB, pode ser o vídeo completo
                print("\nDetectado vídeo completo em um único segmento (tamanho grande).")
                print("Pulando busca por segmentos adicionais.")
                return segment_paths
    else:
        print(f"Erro: Não foi possível baixar o segmento inicial: {base_url}")
        print("Verifique se a URL está correta e tente novamente.")
        return []
    
    # Depois, tenta baixar os segmentos sequenciais
    i = 1  # Começar do segmento 1
    
    # Lista de diferentes padrões de nomeação para tentar
    patterns = [
        # Padrão 001, 002, 003
        lambda url, i: url.replace('.ts', f'_{i:03d}.ts'),
        # Padrão 1, 2, 3
        lambda url, i: url.replace('.ts', f'_{i}.ts'),
        # Padrão quality_720_1.ts
        lambda url, i: url.replace('quality_720.ts', f'quality_720_{i}.ts'),
        # Padrão segment1.ts, segment2.ts
        lambda url, i: url.replace('.ts', f'{i}.ts'),
        # Padrão chunk-1-xxxx.ts
        lambda url, i: url.replace('.ts', f'-{i}.ts'),
    ]
    
    # Testar cada padrão com o primeiro segmento
    current_pattern = None
    for pattern_func in patterns:
        next_url = pattern_func(base_url, i)
        segment_filename = f"segment_{i:03d}{ext}"
        segment_path = temp_dir / segment_filename
        
        print(f"Testando padrão: {next_url}")
        
        if download_segment(next_url, segment_path, session):
            segment_paths.append(segment_path)
            segment_count += 1
            current_pattern = pattern_func
            print(f"Padrão encontrado! Usando: {next_url}")
            break
        else:
            # Remover arquivo vazio ou parcial
            if segment_path.exists():
                segment_path.unlink()
    
    # Se encontrou um padrão, continuar baixando os segmentos
    if current_pattern:
        i = 2  # Começar do próximo segmento
        while i < max_segments and consecutive_failures < 5:
            segment_url = current_pattern(base_url, i)
            segment_filename = f"segment_{i:03d}{ext}"
            segment_path = temp_dir / segment_filename
            
            print(f"Baixando segmento {i}: {segment_url}")
            
            if download_segment(segment_url, segment_path, session):
                segment_paths.append(segment_path)
                segment_count += 1
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                print(f"Falha {consecutive_failures} de 5. Tentando mais alguns segmentos...")
            
            # Pausa para não sobrecarregar o servidor
            time.sleep(SLEEP_BETWEEN_REQUESTS)
            i += 1
    else:
        print("Não foi possível encontrar o padrão de nomenclatura dos segmentos.")
        print("Usando apenas o segmento inicial.")
    
    print(f"\nDownload de segmentos concluído: {segment_count} segmentos baixados")
    
    return segment_paths

def combine_segments(segment_paths, output_path):
    """
    Combina segmentos TS em um único arquivo MP4
    
    Args:
        segment_paths: Lista de caminhos dos segmentos
        output_path: Caminho do arquivo MP4 de saída
        
    Returns:
        bool: True se a combinação foi bem-sucedida
    """
    if not segment_paths:
        print("Erro: Nenhum segmento para combinar")
        return False
    
    print(f"\nCombinando {len(segment_paths)} segmentos em {output_path}")
    
    # Se for apenas um segmento, tentar remuxar diretamente
    if len(segment_paths) == 1:
        print("Detectado segmento único. Tentando remuxar diretamente...")
        
        # Método 1: Remuxar usando ffmpeg (preferencial)
        try:
            # Comando ffmpeg para remuxar TS para MP4
            cmd = get_ffmpeg_command() + [
                "-i", str(segment_paths[0]),
                "-c", "copy",  # Copiar streams sem recodificar
                "-bsf:a", "aac_adtstoasc",  # Necessário para alguns streams AAC
                "-movflags", "+faststart",  # Otimiza para streaming web
                str(output_path)
            ]
            
            print("Executando ffmpeg para remuxar o segmento...")
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                print("Remuxagem com ffmpeg concluída com sucesso!")
                return True
            else:
                print(f"Erro ao remuxar com ffmpeg: {process.stderr}")
                # Continua para métodos alternativos
        except Exception as e:
            print(f"Erro durante remuxagem com ffmpeg: {str(e)}")
            # Continua para métodos alternativos
        
        # Método 2: Usar rename/copy direto se for MP4 mascarado como TS
        try:
            # Verificar conteúdo do arquivo para determinar tipo real
            with open(segment_paths[0], 'rb') as f:
                header = f.read(12)  # Ler primeiros bytes
                
            # Verificar se é um MP4 real (começa com ftyp ou moov)
            is_mp4 = False
            for pattern in [b'ftyp', b'moov']:
                if pattern in header:
                    is_mp4 = True
                    break
            
            if is_mp4:
                print("Detectado cabeçalho MP4 no segmento .ts. Copiando diretamente...")
                shutil.copy2(segment_paths[0], output_path)
                print("Cópia direta concluída.")
                return True
        except Exception as e:
            print(f"Erro durante verificação de cabeçalho: {str(e)}")
            # Continua para métodos alternativos
        
        # Método 3: Usar mkvmerge se disponível (pode lidar com diversos formatos)
        try:
            cmd = ["mkvmerge", "-o", str(output_path), str(segment_paths[0])]
            print("Tentando remuxar com mkvmerge...")
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0 or process.returncode == 1:  # mkvmerge retorna 1 para avisos
                print("Remuxagem com mkvmerge concluída!")
                return True
            else:
                print(f"Erro ao remuxar com mkvmerge: {process.stderr}")
                # Continua para método alternativo
        except Exception as e:
            print(f"Erro ou mkvmerge não disponível: {str(e)}")
            # Continua para método alternativo
    
    # Método para múltiplos segmentos ou se os anteriores falharam
    # Método 4: Concatenação usando o ffmpeg
    try:
        # Criar arquivo de lista de segmentos para o ffmpeg
        segments_list_path = TEMP_DIR / "segments.txt"
        with open(segments_list_path, 'w') as f:
            for segment_path in segment_paths:
                f.write(f"file '{segment_path.absolute()}'\n")
        
        # Comando ffmpeg para concatenar
        cmd = get_ffmpeg_command() + [
            "-f", "concat",
            "-safe", "0",
            "-i", str(segments_list_path),
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",  # Necessário para alguns streams AAC
            "-movflags", "+faststart",  # Otimiza para streaming web
            str(output_path)
        ]
        
        print("Executando ffmpeg para combinar os segmentos...")
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode == 0:
            print("Combinação com ffmpeg concluída com sucesso!")
            return True
        else:
            print(f"Erro ao combinar com ffmpeg: {process.stderr}")
            # Continua para método alternativo
            
    except Exception as e:
        print(f"Erro durante combinação com ffmpeg: {str(e)}")
        # Continua para método alternativo
    
    # Método 5: Usar ffmpeg com protocolo TS
    try:
        print("Tentando método alternativo com ffmpeg (protocolo TS)...")
        # Concatenar todos os arquivos .ts em um único .ts
        ts_concat_path = TEMP_DIR / "concatenated.ts"
        
        with open(ts_concat_path, 'wb') as outfile:
            for segment_path in segment_paths:
                with open(segment_path, 'rb') as infile:
                    outfile.write(infile.read())
        
        # Converter o .ts concatenado para MP4
        cmd = get_ffmpeg_command() + [
            "-i", str(ts_concat_path),
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",
            "-movflags", "+faststart",
            str(output_path)
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        # Limpar arquivo temporário
        if ts_concat_path.exists():
            ts_concat_path.unlink()
        
        if process.returncode == 0:
            print("Remuxagem do TS concatenado concluída com sucesso!")
            return True
        else:
            print(f"Erro ao remuxar o TS concatenado: {process.stderr}")
            # Continua para método alternativo
    except Exception as e:
        print(f"Erro durante remuxagem do TS concatenado: {str(e)}")
        # Continua para método alternativo
    
    # Método 6: Último recurso - concatenação binária
    try:
        print("Tentando método final: cópia binária direta...")
        
        # Se for um único arquivo, copiar diretamente
        if len(segment_paths) == 1:
            shutil.copy2(segment_paths[0], output_path)
            print("Cópia direta concluída.")
            
            # Tentar converter com yt-dlp como último recurso
            try:
                print("Tentando converter com yt-dlp...")
                converted_path = output_path.with_suffix('.converted.mp4')
                
                cmd = [
                    "yt-dlp",
                    "--recode-video", "mp4",
                    "-o", str(converted_path),
                    str(output_path)
                ]
                
                process = subprocess.run(cmd, capture_output=True, text=True)
                
                if process.returncode == 0 and converted_path.exists():
                    # Substituir o arquivo original pelo convertido
                    shutil.move(str(converted_path), str(output_path))
                    print("Conversão com yt-dlp concluída com sucesso!")
                    return True
                else:
                    print("Conversão com yt-dlp falhou. Mantendo arquivo original.")
            except Exception as yt_dlp_error:
                print(f"Erro ao converter com yt-dlp: {str(yt_dlp_error)}")
                print("Mantendo arquivo original.")
            
            return True
        else:
            # Concatenar todos os arquivos
            with open(output_path, 'wb') as outfile:
                for segment_path in segment_paths:
                    with open(segment_path, 'rb') as infile:
                        outfile.write(infile.read())
            
            print("Concatenação direta concluída.")
            
            # Aviso sobre possíveis problemas
            print("\nAVISO: A concatenação direta pode resultar em vídeos corrompidos.")
            print("Se o vídeo não abrir, tente instalar ffmpeg e executar novamente.")
            print("Ou use um conversor online para converter o arquivo TS para MP4.")
            
            return True
    except Exception as inner_e:
        print(f"Erro no método alternativo: {str(inner_e)}")
        return False

def cleanup(segment_paths):
    """Limpa arquivos temporários"""
    try:
        for path in segment_paths:
            if path.exists():
                path.unlink()
        
        segments_list = TEMP_DIR / "segments.txt"
        if segments_list.exists():
            segments_list.unlink()
            
        print("\nLimpeza de arquivos temporários concluída.")
    except Exception as e:
        print(f"Aviso: Erro durante limpeza de arquivos temporários: {str(e)}")

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Baixador de vídeos em segmentos .ts")
    parser.add_argument("url", help="URL do segmento base (ex: site.com/video/quality_720.ts)")
    parser.add_argument("-o", "--output", help="Nome do arquivo de saída")
    parser.add_argument("-s", "--start", type=int, default=0, help="Número do segmento inicial (padrão: 0)")
    parser.add_argument("-m", "--max", type=int, default=500, help="Número máximo de segmentos (padrão: 500)")
    parser.add_argument("--skip-cleanup", action="store_true", help="Não apagar arquivos temporários")
    parser.add_argument("--ffmpeg-path", help="Caminho para o executável do ffmpeg")
    args = parser.parse_args()
    
    print("\n=============================================")
    print(" TS DOWNLOADER - BAIXADOR DE VÍDEOS .TS")
    print("=============================================\n")
    
    # Verificar se ffmpeg está instalado
    global FFMPEG_PATH
    FFMPEG_PATH = None
    
    # Primeiro, tentar o caminho fornecido pelo usuário
    if args.ffmpeg_path:
        try:
            subprocess.run([args.ffmpeg_path, "-version"], capture_output=True, text=True)
            FFMPEG_PATH = args.ffmpeg_path
            print(f"Usando ffmpeg em: {FFMPEG_PATH}")
        except:
            print(f"AVISO: ffmpeg não encontrado em {args.ffmpeg_path}")
    
    # Tentar executável no diretório atual
    if not FFMPEG_PATH:
        try:
            local_ffmpeg = Path("./ffmpeg").absolute()
            if local_ffmpeg.exists():
                subprocess.run([str(local_ffmpeg), "-version"], capture_output=True, text=True)
                FFMPEG_PATH = str(local_ffmpeg)
                print(f"Usando ffmpeg local em: {FFMPEG_PATH}")
        except:
            pass
    
    # Por fim, tentar no PATH do sistema
    if not FFMPEG_PATH:
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
            FFMPEG_PATH = "ffmpeg"
            print("Usando ffmpeg do sistema.")
        except:
            print("AVISO: ffmpeg não encontrado. A combinação de segmentos pode ser menos eficiente.")
    
    # Garantir diretórios
    _, output_dir = ensure_dirs()
    
    # Construir nome do arquivo de saída
    if args.output:
        output_name = args.output
    else:
        # Extrai nome do vídeo da URL
        url_parts = urlparse(args.url)
        path_parts = url_parts.path.split('/')
        
        # Tenta obter um nome significativo
        if len(path_parts) >= 2:
            # Pega o penúltimo segmento da URL, que geralmente tem o nome do vídeo
            video_name = path_parts[-2]
        else:
            video_name = "video"
        
        output_name = f"{video_name}.mp4"
    
    # Caminho completo de saída
    if not output_name.lower().endswith('.mp4'):
        output_name += '.mp4'
    output_path = output_dir / output_name
    
    # Baixar segmentos
    segment_paths = download_all_segments(
        args.url, 
        output_name, 
        start_segment=args.start,
        max_segments=args.max
    )
    
    if not segment_paths:
        print("Erro: Nenhum segmento foi baixado. Verifique a URL e tente novamente.")
        return
    
    # Combinar segmentos
    if combine_segments(segment_paths, output_path):
        print(f"\nVídeo salvo com sucesso em: {output_path}")
        
        # Tamanho do arquivo
        filesize_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"Tamanho do arquivo: {filesize_mb:.2f} MB")
    else:
        print("\nErro ao combinar segmentos. Os segmentos individuais foram mantidos.")
    
    # Limpar arquivos temporários
    if not args.skip_cleanup:
        cleanup(segment_paths)
        print("\nProcesso concluído!")
    else:
        print("\nSegmentos temporários mantidos a pedido do usuário.")
        print(f"Diretório de segmentos: {TEMP_DIR}")

# Definir uma variável global para o caminho do ffmpeg
FFMPEG_PATH = None

def get_ffmpeg_command():
    """Retorna o comando ffmpeg, usando o caminho definido globalmente se disponível"""
    return [FFMPEG_PATH] if FFMPEG_PATH else ["ffmpeg"]

if __name__ == "__main__":
    main() 