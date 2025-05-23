#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ulife Extractor - Navegação assistida para extrair vídeos do Ulife/Ebradi
Este script permite navegar manualmente até a página do vídeo e capturar informações para download
"""

import os
import sys
import json
import time
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def setup_browser():
    """Configura e inicia o navegador Selenium"""
    print("\nConfigurando navegador...")
    
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        print(f"Erro ao iniciar o navegador: {str(e)}")
        sys.exit(1)

def interactive_navigation(driver):
    """Permite navegação interativa até a página do vídeo"""
    print("\n=============================================")
    print(" NAVEGAÇÃO ASSISTIDA - ULIFE EXTRACTOR")
    print("=============================================\n")
    
    print("Navegue manualmente até a página do vídeo e digite 'pronto' quando estiver na página.")
    print("Comandos disponíveis:")
    print("  - pronto: Indica que você chegou à página do vídeo")
    print("  - info: Mostra a URL atual e o título da página")
    print("  - cookies: Mostra os cookies atuais da sessão")
    print("  - source: Salva o código-fonte da página atual")
    print("  - sair: Cancela a navegação e fecha o navegador")
    
    # Abrir portal inicial
    driver.get("https://www.ebradi.com.br/")
    
    while True:
        command = input("\nComando: ").strip().lower()
        
        if command == "pronto":
            break
        elif command == "info":
            print(f"URL atual: {driver.current_url}")
            print(f"Título: {driver.title}")
        elif command == "cookies":
            cookies = driver.get_cookies()
            print(f"Cookies ({len(cookies)}): {json.dumps(cookies, indent=2)}")
        elif command == "source":
            with open("page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("Código-fonte salvo em page_source.html")
        elif command == "sair":
            print("Navegação cancelada.")
            driver.quit()
            sys.exit(0)
        else:
            print("Comando desconhecido.")
    
    print("\nPágina do vídeo identificada!")
    return capture_video_info(driver)

def capture_video_info(driver):
    """Captura informações do vídeo da página atual"""
    print("\nCapturando informações do vídeo...")
    
    url = driver.current_url
    title = driver.title
    cookies = driver.get_cookies()
    
    # Salvar cookies para uso posterior
    with open("selenium_cookies.json", "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=2)
    
    # Analisar network para encontrar URLs de vídeo
    print("\nAnalisando rede para encontrar URLs de vídeo...")
    
    # Aqui você adicionaria código para capturar requisições de rede
    # Isso normalmente requer extensões do Selenium ou usar o Chrome DevTools Protocol
    
    # Para simplificar, pedimos ao usuário para verificar manualmente
    print("\nVerifique a aba Network nas ferramentas de desenvolvedor do navegador")
    print("Procure por arquivos .ts ou .m3u8 durante a reprodução do vídeo")
    ts_url = input("\nDigite a URL do segmento .ts encontrado: ").strip()
    
    if ts_url:
        print(f"\nURL do segmento .ts capturada: {ts_url}")
        print("Use esta URL com o script ts_downloader.py para baixar o vídeo completo:")
        print(f"python ts_downloader.py \"{ts_url}\" -o video.mp4")
    else:
        print("Nenhuma URL fornecida.")
    
    return ts_url

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Navegação assistida para extrair vídeos do Ulife/Ebradi")
    parser.add_argument("-o", "--output", help="Nome do arquivo de saída")
    args = parser.parse_args()
    
    driver = setup_browser()
    
    try:
        ts_url = interactive_navigation(driver)
        
        if ts_url and args.output:
            print(f"\nBaixando vídeo para {args.output}...")
            # Aqui você poderia chamar diretamente o ts_downloader
            os.system(f"python ts_downloader.py \"{ts_url}\" -o \"{args.output}\"")
            print("\nDownload concluído!")
    finally:
        print("\nFechando navegador...")
        driver.quit()

if __name__ == "__main__":
    main() 