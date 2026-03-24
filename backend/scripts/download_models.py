"""
模型预下载脚本
用于提前下载NER模型和Cross-Encoder模型到本地缓存

使用方法:
    cd backend
    uv run python scripts/download_models.py
"""

import os
import sys
import time
from pathlib import Path

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

MODELS_DIR = backend_dir / "huggingface_models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

NER_MODEL_NAME = "uer/roberta-base-finetuned-cluener2020-chinese"
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

NER_MODEL_DIR = MODELS_DIR / "ner_model"
RERANKER_MODEL_DIR = MODELS_DIR / "reranker_model"


def download_ner_model():
    print("\n" + "=" * 60)
    print("下载NER模型 (实体识别)")
    print(f"模型名称: {NER_MODEL_NAME}")
    print(f"保存路径: {NER_MODEL_DIR}")
    print("=" * 60)
    
    try:
        from transformers import AutoTokenizer, AutoModelForTokenClassification
        
        start_time = time.time()
        
        print("\n正在下载tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(NER_MODEL_NAME)
        
        print("正在下载模型权重...")
        model = AutoModelForTokenClassification.from_pretrained(NER_MODEL_NAME)
        
        print("正在保存到本地...")
        NER_MODEL_DIR.mkdir(parents=True, exist_ok=True)
        tokenizer.save_pretrained(str(NER_MODEL_DIR))
        model.save_pretrained(str(NER_MODEL_DIR))
        
        elapsed = time.time() - start_time
        print(f"\n[OK] NER模型下载完成! 耗时: {elapsed:.2f}秒")
        print(f"   保存位置: {NER_MODEL_DIR}")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] NER模型下载失败: {str(e)}")
        return False


def download_reranker_model():
    print("\n" + "=" * 60)
    print("下载Cross-Encoder模型 (重排序)")
    print(f"模型名称: {RERANKER_MODEL_NAME}")
    print(f"保存路径: {RERANKER_MODEL_DIR}")
    print("=" * 60)
    
    try:
        from sentence_transformers import CrossEncoder
        
        start_time = time.time()
        
        print("\n正在下载模型...")
        model = CrossEncoder(RERANKER_MODEL_NAME)
        
        print("正在保存到本地...")
        RERANKER_MODEL_DIR.mkdir(parents=True, exist_ok=True)
        model.save(str(RERANKER_MODEL_DIR))
        
        elapsed = time.time() - start_time
        print(f"\n[OK] Cross-Encoder模型下载完成! 耗时: {elapsed:.2f}秒")
        print(f"   保存位置: {RERANKER_MODEL_DIR}")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Cross-Encoder模型下载失败: {str(e)}")
        return False


def check_models():
    print("\n" + "=" * 60)
    print("检查已下载的模型")
    print("=" * 60)
    
    ner_config = NER_MODEL_DIR / "config.json"
    ner_model = NER_MODEL_DIR / "pytorch_model.bin"
    ner_tokenizer = NER_MODEL_DIR / "tokenizer.json"
    
    print(f"\nNER模型 ({NER_MODEL_NAME}):")
    print(f"  - config.json: {'[OK] 存在' if ner_config.exists() else '[X] 不存在'}")
    print(f"  - pytorch_model.bin: {'[OK] 存在' if ner_model.exists() else '[X] 不存在'}")
    print(f"  - tokenizer.json: {'[OK] 存在' if ner_tokenizer.exists() else '[X] 不存在'}")
    
    reranker_config = RERANKER_MODEL_DIR / "config.json"
    reranker_model = RERANKER_MODEL_DIR / "pytorch_model.bin"
    reranker_tokenizer = RERANKER_MODEL_DIR / "tokenizer.json"
    
    print(f"\nCross-Encoder模型 ({RERANKER_MODEL_NAME}):")
    print(f"  - config.json: {'[OK] 存在' if reranker_config.exists() else '[X] 不存在'}")
    print(f"  - pytorch_model.bin: {'[OK] 存在' if reranker_model.exists() else '[X] 不存在'}")
    print(f"  - tokenizer.json: {'[OK] 存在' if reranker_tokenizer.exists() else '[X] 不存在'}")


def main():
    print("\n" + "=" * 60)
    print("       法律AI助手 - 模型预下载工具")
    print("=" * 60)
    print(f"\n模型存储目录: {MODELS_DIR}")
    
    print("\n即将下载以下模型:")
    print(f"  1. NER模型 (约400MB): {NER_MODEL_NAME}")
    print(f"  2. Cross-Encoder模型 (约90MB): {RERANKER_MODEL_NAME}")
    
    print("\n提示: 首次下载需要从Hugging Face获取模型，请确保网络连接正常")
    
    choice = input("\n是否开始下载? (y/n): ").strip().lower()
    if choice != 'y':
        print("已取消下载")
        check_models()
        return
    
    ner_success = download_ner_model()
    reranker_success = download_reranker_model()
    
    print("\n" + "=" * 60)
    print("下载结果汇总")
    print("=" * 60)
    print(f"NER模型: {'[OK] 成功' if ner_success else '[X] 失败'}")
    print(f"Cross-Encoder模型: {'[OK] 成功' if reranker_success else '[X] 失败'}")
    
    check_models()
    
    print("\n提示: 模型下载完成后，后续启动服务将直接从本地加载，无需再次下载")


if __name__ == "__main__":
    main()
