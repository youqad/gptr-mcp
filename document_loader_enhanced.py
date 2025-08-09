"""
Enhanced Document Loader for GPT-Researcher MCP
Supports additional file formats including source code and academic documents
"""

import asyncio
import os
from typing import List, Union
from langchain_community.document_loaders import (
    PyMuPDFLoader,
    TextLoader,
    UnstructuredCSVLoader,
    UnstructuredExcelLoader,
    UnstructuredMarkdownLoader,
    UnstructuredPowerPointLoader,
    UnstructuredWordDocumentLoader,
    BSHTMLLoader
)


class EnhancedDocumentLoader:
    
    TEXT_EXTENSIONS = {
        'tex', 'bib', 'cls', 'sty',
        'org',
        'rst',
        'adoc', 'asciidoc',
        
        'py', 'pyx', 'pyi',
        'hs', 'lhs',
        'ml', 'mli',
        'agda',
        'lean',
        'v',
        'idr',
        'scala', 'sc',
        'kt', 'kts',
        'java',
        'js', 'jsx', 'ts', 'tsx', 'mjs',
        'go',
        'rs',
        'c', 'h', 'cpp', 'cc', 'cxx', 'hpp', 'hxx',
        'cs',
        'swift',
        'r', 'R',
        'jl',
        'm',
        'f90', 'f95', 'f03',
        'pl', 'pm',
        'rb',
        'php',
        'lua',
        'sh', 'bash', 'zsh', 'fish',
        'ps1',
        'clj', 'cljs', 'cljc',
        'elm',
        'ex', 'exs',
        'erl', 'hrl',
        'nim',
        'dart',
        'zig',
        
        'json', 'jsonl',
        'yaml', 'yml',
        'toml',
        'ini', 'cfg', 'conf',
        'xml',
        'sql',
        'graphql', 'gql',
        
        'css', 'scss', 'sass', 'less',
        'vue',
        'svelte',
        
        'readme', 'license', 'changelog', 'authors',
        'todo',
        
        'log',
        'diff', 'patch',
        'vim',
        'el',
    }
    
    def __init__(self, path: Union[str, List[str]]):
        self.path = path

    async def load(self) -> list:
        tasks = []
        if isinstance(self.path, list):
            for file_path in self.path:
                if os.path.isfile(file_path):
                    filename = os.path.basename(file_path)
                    file_name, file_extension_with_dot = os.path.splitext(filename)
                    file_extension = file_extension_with_dot.strip(".").lower()
                    
                    if not file_extension and file_name.lower() in self.TEXT_EXTENSIONS:
                        file_extension = 'txt'
                    
                    tasks.append(self._load_document(file_path, file_extension))
                    
        elif isinstance(self.path, (str, bytes, os.PathLike)):
            for root, dirs, files in os.walk(self.path):
                dirs[:] = [d for d in dirs if d not in {
                    '.git', '__pycache__', 'node_modules', '.venv', 'venv',
                    'dist', 'build', '.pytest_cache', '.mypy_cache'
                }]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    file_name, file_extension_with_dot = os.path.splitext(file)
                    file_extension = file_extension_with_dot.strip(".").lower()
                    
                    if not file_extension and file.lower() in self.TEXT_EXTENSIONS:
                        file_extension = 'txt'
                    
                    tasks.append(self._load_document(file_path, file_extension))
                    
        else:
            raise ValueError("Invalid type for path. Expected str, bytes, os.PathLike, or list thereof.")

        docs = []
        for pages in await asyncio.gather(*tasks):
            for page in pages:
                if page.page_content:
                    docs.append({
                        "raw_content": page.page_content,
                        "url": os.path.basename(page.metadata['source'])
                    })
                    
        if not docs:
            raise ValueError("🤷 Failed to load any documents!")

        return docs

    async def _load_document(self, file_path: str, file_extension: str) -> list:
        ret_data = []
        try:
            loader_dict = {
                "pdf": PyMuPDFLoader(file_path),
                "txt": TextLoader(file_path, encoding='utf-8', autodetect_encoding=True),
                "doc": UnstructuredWordDocumentLoader(file_path),
                "docx": UnstructuredWordDocumentLoader(file_path),
                "pptx": UnstructuredPowerPointLoader(file_path),
                "csv": UnstructuredCSVLoader(file_path, mode="elements"),
                "xls": UnstructuredExcelLoader(file_path, mode="elements"),
                "xlsx": UnstructuredExcelLoader(file_path, mode="elements"),
                "md": UnstructuredMarkdownLoader(file_path),
                "html": BSHTMLLoader(file_path),
                "htm": BSHTMLLoader(file_path)
            }

            if file_extension in self.TEXT_EXTENSIONS:
                loader = TextLoader(file_path, encoding='utf-8', autodetect_encoding=True)
            else:
                loader = loader_dict.get(file_extension, None)
            
            if loader:
                try:
                    ret_data = loader.load()
                except UnicodeDecodeError:
                    try:
                        loader = TextLoader(file_path, encoding='latin-1')
                        ret_data = loader.load()
                    except Exception as e:
                        print(f"Failed to load document with encoding issues: {file_path}")
                        print(e)
                except Exception as e:
                    print(f"Failed to load document: {file_path}")
                    print(e)

        except Exception as e:
            print(f"Failed to process document: {file_path}")
            print(e)

        return ret_data