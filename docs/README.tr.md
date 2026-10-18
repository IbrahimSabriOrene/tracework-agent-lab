# Tracework Türkçe kullanım rehberi

Tracework, kurgu proje belgelerini inceleyen bağımsız bir AI agent demosudur. Gerçek LangGraph iş
akışını, Harness² çekirdeğine yazılmış özel bir belge inceleme adaptörüyle birleştirir.

## Demo neyi gösteriyor

Belge okunur, bulgular üretilir, her alıntı kaynak satırına göre doğrulanır ve iş akışı insan onayı
bekler. Onay verilirse tek bir yerel rapor kaydedilir. Belgenin içindeki “beni onayla” gibi ifadeler
insan kararı yerine geçmez. Gerçek kişilere mesaj veya dış sisteme komut gönderilmez.

Varsayılan inceleyici açık kurallarla çalışan bir simülasyondur; LLM olarak sunulmaz. Harness² deney
döngüsü gerçektir, ancak düzenleyici önceden tanımlı profil değişikliğini uygular. Bu, kendiliğinden
öğrenen bir model veya yeni strateji keşfi iddiası değildir. İstenirse yerel incelemede Ollama modeli
kullanılabilir; deney düzenleyicisi bu durumda da betik tabanlı kalır.

## Hızlı başlatma

```bash
git clone https://github.com/IbrahimSabriOrene/tracework-agent-lab.git
cd tracework-agent-lab
docker compose up --build -d
```

Tarayıcıda `http://127.0.0.1:8765` adresini açın. Docker yolu Windows'ta da tam deney akışını sunar.
Harness² çekirdeğinin Linux/POSIX dosya kilidi kullanması nedeniyle deneyleri Windows Python'ında
çalıştırmak yerine Docker veya WSL kullanın.

Python 3.12/3.13 ve uv ile yerel belge inceleme:

```bash
uv sync --locked
uv run tracework serve
```

## Önerilen gösterim

1. Atlas belgesini Baseline profiliyle inceleyin.
2. Evidence-aware profiline geçip yeniden çalıştırın. Bulgulardan kaynak satırına gidin.
3. Execution trace bölümünde adımları inceleyin.
4. Bir raporu onaylayın; JSON çıktısını indirin. Başka bir raporu reddedin.
5. Onay bekleyen bir iş varken uygulamayı yeniden başlatın ve yerel geçmişten devam edin.
6. Cedar belgesindeki gömülü talimatın onay oluşturmadığını kontrol edin.
7. Harness experiments sekmesinde iki profilin bağımsız örneklerdeki sonuçlarını ve gerçek yürütme
   kayıtlarını inceleyin.

## GitHub'daki canlı tanıtımın sınırı

GitHub Pages sürümü, gerçek yerel yürütmelerden üretilmiş kayıtları etkileşimli oynatır. Python
backend'i, canlı model veya kalıcı onay kaydı içermez. Arayüz bu modu açıkça belirtir. Kendi metninizi
incelemek ve gerçek deney başlatmak için yerel uygulamayı açın.

## Deney ve test

```bash
uv run tracework experiment --mode sequential --output .data/my-experiment
uv run tracework evaluate
uv run pytest -q
```

İlk iki geliştirme belgesi harness döngüsüne girer; dört ayrı kurgu belge değerlendirme için tutulur.
Beklenen etiketler düzenleyiciye/seçiciye verilmez. Örnekler küçük ve kurallarla birlikte yazılmıştır;
buradaki yüzde değerleri gerçek dünya LLM başarısı veya üretime hazır olma kanıtı değildir.

Mimari için [architecture.md](architecture.md), deney yöntemi için [experiments.md](experiments.md),
API örnekleri için [api.md](api.md) dosyalarına bakın. Orijinal uygulama MIT, ayrı Harness² bağımlılığı
Apache-2.0 lisanslıdır. Bu bağımsız demo Google veya LangChain'in resmî ürünü değildir.
