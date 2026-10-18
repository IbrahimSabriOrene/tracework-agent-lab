# Tracework nasıl test edilir?

[Proje özeti](README.tr.md) · [English test guide](testing.md) · [Mimari açıklaması](architecture.md)

Önce canlı tanıtımda etkileşimi inceleyin. Ardından yerel uygulamada gerçek Python iş akışını,
kalıcı kayıtları ve yeni Harness² deneylerini test edin. Varsayılan çevrimdışı mod API anahtarı
gerektirmez.

## Hangi ortamda neyi test ediyoruz?

| Özellik | [GitHub Pages tanıtımı](https://ibrahimsabriorene.github.io/tracework-agent-lab/) | Yerel uygulama |
| --- | --- | --- |
| Altı örnek belge ve iki profil | Kaydedilmiş sonuçlar | Her seferinde gerçek yürütme |
| Kaynak alıntısı ve işlem adımları | Etkileşimli inceleme | Etkileşimli inceleme |
| Onay, ret ve JSON indirme | Geçici kayıt oynatımı | Kalıcı yerel rapor |
| Kendi metninizi inceleme | Yok | Var |
| MinerU ile PDF yükleme | Yok | İsteğe bağlı kurulum; gerçek yerel CPU OCR |
| Sunucu yeniden başladıktan sonra devam | Yok | SQLite checkpoint ile var |
| Yeni Harness² deneyi | Yok; önceki deneyin kaydı gösterilir | Docker/Linux/WSL ile var |
| Yerel Ollama modeli | Yok | İsteğe bağlı |

![Yerel inceleme, izole deney ve canlı tanıtımın sınırları](images/architecture.png)

Görsel bu deponun yapısını anlatır. Harness² ile LangGraph arasındaki bağlantıyı özel adaptör
kurar. Deneyde çıkan prompt, çalışan uygulamaya otomatik aktarılmaz.

## 1. Beş dakikalık tarayıcı testi

[Canlı tanıtımı açın](https://ibrahimsabriorene.github.io/tracework-agent-lab/). Üstte
**Interactive replay** yazısını kontrol edin. Aşağıdaki adımlar yerel uygulamada da geçerlidir.

1. **Review workspace** bölümünde **Atlas launch brief** belgesini seçin. **Baseline** ile
   **Run review** düğmesine basın. Atanmamış sorumlu hakkında **1 bulgu** gelmeli.
2. **Evidence-aware** ile yeniden çalıştırın. Sorumlu, belirsiz tarih ve bekleyen bağımlılık
   hakkında **3 bulgu** gelmeli. Akış insan kararını beklemeli.
3. Bir bulgudaki **Inspect source** düğmesine basın. Alıntının geçtiği kaynak satırı
   vurgulanmalı. **Execution trace** bölümünü açıp adımları inceleyin.
4. **Approve & publish**, ardından **Download JSON report** düğmesine basın. Canlı tanıtımda
   **Replay report ready**, yerelde **Published locally** yazmalı. Onay, inceleme raporunun
   kaydedilmesine yöneliktir; kaynak projeyi onaylamaz veya dışarıya mesaj göndermez.
5. **Cedar handoff notes** belgesini **Evidence-aware** ile çalıştırın. Gömülü talimat dahil
   **2 bulgu** gelmeli. Belgedeki “beni onayla” ifadesi kendi başına onay oluşturamamalı.
   **Reject publication** ile reddedin; bu iş için yayımlanmış rapor oluşmamalı.
6. **Maple complete brief** belgesini iki profille de çalıştırın. **0 bulgu** gelmeli.
7. **Harness experiments** bölümünde yürütme kaydını açın. Canlı tanıtımda gördüğünüz sonuç,
   yeni başlatılan deney değil, önceden çalıştırılmış deneyin kaydıdır.

![Kaynak kanıtı ve işlem adımlarıyla belge inceleme ekranı](images/workspace.png)

### Çevrimdışı modda beklenen bulgu sayıları

| Belge | Baseline | Evidence-aware | Kontrol edilen durum |
| --- | ---: | ---: | --- |
| Atlas launch brief | 1 | 3 | Sorumlu, tarih, bağımlılık |
| Cedar handoff notes | 1 | 2 | Kabul kriteri ve gömülü talimat |
| Lumen release checklist | 1 | 3 | Geri dönüş planı, tarih, bağımlılık |
| Harbor proposal | 2 | 2 | Sorumlu ve kabul kriteri |
| Willow review note | 0 | 1 | Gömülü talimat |
| Maple complete brief | 0 | 0 | Temiz kontrol örneği |

Bu sayılar açık kurallarla çalışan varsayılan motor ve onun kayıtları içindir. Ollama modeli
farklı sonuç verebilir. Sıfır bulgu, kuralların eşleşme bulamadığını gösterir; belgenin eksiksiz
ve doğru olduğunu garanti etmez.

## 2. Gerçek yerel uygulamayı başlatma

Git, Docker ve Docker Compose kurulu, Docker çalışır durumda olmalı:

```bash
git clone https://github.com/IbrahimSabriOrene/tracework-agent-lab.git
cd tracework-agent-lab
docker compose up --build -d
```

**http://127.0.0.1:8765** adresini açın. Üstte **Local application** yazmalı.
**http://127.0.0.1:8765/api/health** aktif motoru gösterir. Hazır Compose ayarı `offline`
kullanır. İlk kurulumda bağımlılıklar indirildiği için internet bağlantısı gerekir.

Yukarıdaki tarayıcı testlerini tekrarlayın. Sonra **Edit document** ile şu metni girin:

```text
# Demo review
Delivery owner: TBD.
Review is planned for tomorrow.
Dependency: design sign-off is pending.
Acceptance criteria: not defined.
```

**View source** ile kaynak görünümüne dönüp iki profili çalıştırın. Baseline **2**, Evidence-aware
**4 bulgu** üretmeli. Onay sonrasında yerel JSON raporu indirilebilmeli.

PDF yüklemek için [MinerU kurulum ve taranmış PDF rehberini](pdf.tr.md) izleyin.
`scripts/check_browser.py --pdf` gerçek OCR, inceleme, onay ve kaynak bilgisi çıktısını test eder.

## 3. Yeniden başlatma, onay ve ret testi

1. Yeni bir Atlas incelemesi başlatın, karar vermeyin. **Recent local reviews** listesindeki
   son kaydı not alın. Tam çalışma kimliğini `/api/runs` veya inceleme API yanıtından alın.
2. Verileri silmeden uygulamayı yeniden başlatın:

   ```bash
   docker compose restart lab
   ```

3. Sunucu açılınca sayfayı yenileyin. **Recent local reviews** listesinden aynı işi açın.
   Bulgular ve bekleyen karar korunmuş olmalı.
4. Onaylayıp JSON raporunu indirin. Rapordaki `run_id` aynı işe ait olmalı. İşi yeniden
   açtığınızda yayımlanmış durumda kalmalı ve tekrar karar istememeli.
5. Başka bir işte ret verin. O iş için yayımlanmış rapor oluşmamalı.

Docker verileri adlandırılmış volume içinde tutar. `docker compose down` verileri koruyarak
uygulamayı durdurur. Volume silinirse inceleme geçmişi de silinir.

HTTP kontrolleri için **http://127.0.0.1:8765/docs** ve [API örneklerini](api.md) kullanın.
Onaydan önce rapor endpoint'i **404**, tamamlanmış işe ikinci karar isteği **409**, boolean
yerine `"approved": "yes"` gönderilmesi **422** dönmeli. Otomatik testler, rapor kaydetme
adımına tekrar karar gönderildiğinde ikinci bir yerel rapor oluşmadığını da doğrular.

## 4. Gerçek Harness² deneyi

Docker uygulaması çalışırken **Harness experiments** bölümünde sequential veya parallel
seçip **Run Harness² experiment** düğmesine basın. **Experiment completed** yazmalı;
yürütme kaydı upstream commit'i ve yeni LangGraph çalışmalarını göstermeli.

Komut satırından sonuç dosyalarını üretmek için:

```bash
docker compose exec lab tracework experiment --mode sequential --budget 1 --output .data/manual-sequential
docker compose exec lab tracework experiment --mode parallel --budget 1 --output .data/manual-parallel
docker compose exec lab tracework evaluate
```

Yeni deney için yeni çıktı klasörü kullanın; var olan klasör önceki deneye devam etmek için
kullanılabilir. `experiment.json` ile aday, işlem izi, seçim ve reflection kayıtlarını inceleyin.
Örneğin sequential deney dosyalarını bilgisayarınıza kopyalayın:

```bash
docker compose cp lab:/app/.data/manual-sequential ./manual-sequential-results
```

Beklenen davranışlar:

- Gerçek upstream deney döngüsü **iki geliştirme belgesi** üzerinde çalışır.
- Aday testleri temiz LangGraph durumuyla başlar, insan onayında durur ve rapor yayımlamaz.
- Yalnızca izin verilen prompt ayarı değişir; kanıt doğrulama ve insan onayı sabit kalır.
- Düzenleyici kendisini **scripted** olarak belirtir. Model eğitimi yapılmaz.
- Ayrı değerlendirmede **dört holdout belgesi** kullanılır. Bu kurgu örneklerde kural yakalama
  oranı (recall) **%50 → %100**, bulunan kuralların doğruluk oranı (precision) iki profilde de
  **%100** çıkar.

Bu küçük, kurallarla birlikte yazılmış veri kümesi genel AI başarısını ölçmez. Paylaşmadan önce
[deney yöntemini ve sınırlarını](experiments.md) okuyun.

![Harness deney ekranı ve iki profilin karşılaştırılması](images/experiments.png)

## 5. Otomatik testler

Python 3.12/3.13 ve uv ile depo kökünde:

```bash
uv sync --locked
uv run ruff check tracework tests
uv run ruff format --check tracework tests
uv run pytest -q
```

Mevcut pakette **15 test durumu** vardır. Linux'ta tamamı çalışır. Windows Python'ında on üçü
çalışır, upstream POSIX `fcntl` kilidi gerektiren iki Harness² testi atlanır. Windows'ta tüm
paketi çalıştırmak için Docker kullanın:

```bash
docker build --target test -t tracework-test .
docker run --rm tracework-test
```

Kapsam: yeniden başlatıp devam etme, ret, kaynak alıntısı, yinelenen bulgular, tek rapor,
API doğrulama, farklı tarayıcı origin'inden değişiklik isteğinin reddi, dokümantasyon politikası,
adayın değiştirebileceği dosya sınırları ve iki modda gerçek Harness² döngüsü.

### Tarayıcı otomasyonu

Yerel uygulama çalışırken depo kökünde:

```bash
uv run --with playwright playwright install chromium
uv run --with playwright python scripts/check_browser.py
```

Kaynak satırının vurgulanması, onay, ret, JSON indirme, gezinme, HTML benzeri metnin güvenli
gösterimi ve 390 px mobil görünüm kontrol edilir. Ekran görüntüleri `docs/images/` altına
kaydedilir; mevcut arayüz görsellerinin üzerine yazılır. [Mobil ekran görüntüsü](images/mobile.png).

Statik kayıt sürümünü test etmek için bir terminalde:

```bash
python -m http.server 8080 --directory web
```

Başka bir terminalde:

```bash
uv run --with playwright python scripts/check_browser.py --url http://127.0.0.1:8080 --replay
```

[GitHub Checks](https://github.com/IbrahimSabriOrene/tracework-agent-lab/actions/workflows/checks.yml)
Linux üzerinde Python 3.12/3.13 ve tarayıcı kontrollerini çalıştırır. İncelediğiniz commit'in
sonucuna bakın; bir rozet her bilgisayar ve modelin test edildiği anlamına gelmez.

## Model testi ve sorun giderme

Model kurulumunu README'nin [Optional local-model review](../README.md#optional-local-model-review)
bölümünden yapın. Bilgisayarınızdaki Ollama'ya bağlanmanın en basit yolu native Python
sunucusudur; hazır Compose servisi çevrimdışı kalır. Testten önce `/api/health` kontrol edin.
Tablodaki kesin bulgu sayıları model için geçerli değildir. Hem alıntı eşleşmesini hem bulgunun
anlamını kontrol edin. Varsayılan otomatik test paketi canlı model çağrısı yapmaz.

| Sorun | Kontrol |
| --- | --- |
| Yerel uygulama yerine replay açılıyor | Backend'i başlatın; Pages veya statik sunucu yerine 8765 portunu açın |
| Windows'ta deney hatası | Docker, Linux veya WSL kullanın |
| 8765 portu kullanımda | Diğer sunucuyu durdurun; native sunucu ve Compose aynı portu kullanmasın |
| Yeniden başlatınca geçmiş boş | Aynı veri klasörünün veya volume'ün korunduğunu kontrol edin |
| Model erişilemiyor veya çıktı geçersiz | Ollama, kurulu model ve ortam değişkenlerini kontrol edin; sessiz fallback yoktur |
| Kurumsal bilgisayarda uv sertifika hatası | Onaylı sistem sertifikalarını kullanın; uv `--system-certs` destekler |

Hata bildirirken commit, işletim sistemi, çalışma modu, motor, belge/profil, beklenen ve alınan
sonuç ile kişisel veri içermeyen işlem kaydını ekleyin. Yalnızca kurgu belge paylaşın.

## Terimler

| Terim | Bu demoda anlamı |
| --- | --- |
| Agent iş akışı | LangGraph'ın yönettiği, durum tutan inceleme adımları ve izinli geçişler |
| Finding / bulgu | Kural, kaynak alıntısı, satır numarası ve öneri içeren inceleme sonucu |
| Harness | Sabit inceleyicinin çevresindeki ayarlar; bu demoda izinli prompt metni değişir |
| Checkpoint | Aynı bekleyen işe devam etmeyi sağlayan kayıtlı graph durumu |
| Trace | İş akışındaki adımların incelenebilir kaydı |
| Probe | Rapor yayımlamadan durdurulan izole aday testi |
| Holdout | Deneyin geliştirme akışına girmeyen ayrı değerlendirme belgeleri |
| Publication | İnsan onayından sonra bir inceleme raporunun yerel kaydı |
