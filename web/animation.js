/* A deterministic educational storyboard; it never calls a model or backend. */
(() => {
  const duration = 48000, sceneLength = 6000;
  const $ = (id) => document.getElementById(id);
  const color = { ink: "#183447", muted: "#627783", line: "#dce5e9", teal: "#176d70", soft: "#e3f1ee", purple: "#7152a3", violet: "#f2edf8", amber: "#ac721a", rose: "#b65252" };
  const scenes = [
    ["PDF / metin", "PDF, yerelde inceleme metnine dönüşür.", "MinerU Basic / ONNX → metni kontrol et → LangGraph incelemesi", "PDF girişi isteğe bağlıdır. OCR yereldir; API anahtarı veya bulut servisi kullanılmaz."],
    ["LangGraph", "LangGraph, incelemenin adımlarını yönetir.", "StateGraph: read → review → verify → approval → publish / end", "Varsayılan motor açık kurallarla çalışır. Yerel incelemede Ollama isteğe bağlıdır."],
    ["Kanıt", "Her bulgu kaynak satırına bağlanır.", "Doğrulama, değiştirilebilir prompt metninin dışında uygulanır.", "Alıntı ve satır birebir eşleşmeli; desteklenmeyen ve yinelenen bulgular tutulmaz."],
    ["İnsan onayı", "Akış insan kararı için durur.", "interrupt() bekler; SQLiteSaver, graph durumunu saklar.", "Aynı kalıcı veriyle uygulama yeniden başlasa da bekleyen incelemeye devam edilir."],
    ["Devam ve rapor", "İnsan kararı, aynı işi devam ettirir.", "Command(resume=...) → koşullu geçiş → publish veya end", "Onay bir yerel inceleme raporu kaydeder. Ret durumunda rapor yayımlanmaz."],
    ["Harness²", "Harness², prompt adaylarını izole dener.", "Gerçek upstream çekirdek + bu demo için yazılmış özel belge adaptörü", "ScriptedEditor önceden tanımlı profili değiştirir; model eğitimi yapılmaz."],
    ["Adaptör", "Her aday, temiz bir LangGraph üzerinde test edilir.", "DocumentAdapter.execute() → yeni graph → bulgular + işlem izleri", "Probe insan onayında durur. Deney, çalışan uygulamanın prompt'unu otomatik değiştirmez."],
    ["Canlı demo", "Paylaşılan demo, kaydedilmiş sonuçları oynatır.", "Yerel graph çalışmaları → replay.json → etkileşimli GitHub Pages", "Yeni inceleme, kalıcı karar ve yeni Harness² deneyleri yerel uygulamada çalışır."],
  ];
  const esc = (value) => String(value).replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const text = (x,y,value,size=25,fill=color.ink,weight=400,anchor="start") => `<text x="${x}" y="${y}" fill="${fill}" font-size="${size}" font-weight="${weight}" text-anchor="${anchor}">${esc(value)}</text>`;
  const box = (x,y,w,h,fill="white",stroke=color.line,r=12) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="${fill}" stroke="${stroke}" stroke-width="2"/>`;
  function card(x,y,w,h,title,subtitle,active=false,accent=color.teal) {
    return box(x,y,w,h,active ? (accent === color.purple ? color.violet : color.soft) : "white",active?accent:color.line)
      + text(x+24,y+48,title,28,color.ink,600) + text(x+24,y+85,subtitle,21,color.muted);
  }
  function wire(points,active,p,accent=color.teal) {
    const [x1,y1,x2,y2] = points;
    const packet = active ? `<circle cx="${x1+(x2-x1)*p}" cy="${y1+(y2-y1)*p}" r="8" fill="${accent}" stroke="white" stroke-width="3"/>` : "";
    return `<path d="M${x1} ${y1}L${x2} ${y2}" fill="none" stroke="${active?accent:'#bdcfd6'}" stroke-width="3" marker-end="url(#arrow${active?'Active':''})"/>${packet}`;
  }
  function reviewGraph(stage,p) {
    const names = [["Belge","Güvenilmeyen metin"],["İnceleme","Kurallar / yerel model"],["Kanıt kontrolü","Alıntı + satır eşleşmesi"],["İnsan kararı","interrupt() / resume"],["Yerel rapor","İş başına tek kayıt"]];
    let svg = text(72,260,"LangGraph · Durum tutan yürütme",24,color.teal,600);
    names.forEach(([name,sub],i) => {
      const x = 72+i*304;
      svg += card(x,290,240,132,name,sub,i===stage);
      svg += text(x+24,400,["read","review","verify","approval","publish"][i],18,color.muted);
      if(i<4) svg += wire([x+248,356,x+294,356],stage===i+1,p);
    });
    return svg;
  }
  function reviewDetail(stage,p) {
    if(stage===0) return box(72,485,900,210,"#f8fafb")
      + text(100,528,"Atlas launch brief · kurgu belge",25,color.ink,600)
      + text(100,572,"5   Content owner: TBD.",25,color.muted)
      + text(100,612,"6   The design review happens next Friday.",25,color.muted)
      + text(100,652,"7   Dependency: venue confirmation is pending.",25,color.muted)
      + text(1020,555,"Belge = veri",32,color.teal,600)+text(1020,600,"Karar yetkisi insanda kalır.",24,color.muted);
    if(stage===1) return card(72,498,420,180,"Baseline","Eksik alan kontrolleri",p<0.5)
      + text(96,640,"Atlas: 1 bulgu",26,color.teal,600)
      + wire([510,585,650,585],true,p)
      + card(680,498,470,180,"Evidence-aware","Daha geniş inceleme ipuçları",p>=0.5)
      + text(704,640,"Atlas: 3 bulgu",26,color.teal,600)
      + text(1200,554,"Aynı belge",26,color.ink,600)+text(1200,596,"İki izinli profil",24,color.muted)
      + text(1200,638,"Offline sonuçlar",22,color.muted);
    if(stage===2) return box(72,492,920,190,"#f8fafb")
      + text(100,539,"Bulgu: Atanmamış sorumlu",27,color.ink,600)
      + box(100,560,860,58,color.soft,color.teal,6)
      + text(120,598,'5   Content owner: TBD.',27,color.teal,600)
      + text(100,655,"quote == source_lines[line - 1]",25,color.muted)
      + text(1040,548,"✓ Tam satır eşleşmesi",27,color.teal,600)
      + text(1040,595,"✓ Yinelenen bulgu kontrolü",25,color.teal)
      + text(1040,642,"Yorumun doğruluğunu insan inceler.",22,color.muted);
    if(stage===3) return box(72,500,620,170,"#fff7e9","#e4c891")
      + text(100,547,"interrupt()",31,color.amber,600)
      + text(100,590,"Durum: awaiting_review",27,color.ink)
      + text(100,632,"Yayımlanmış rapor henüz yok.",24,color.muted)
      + wire([710,582,850,582],true,p)
      + card(880,500,648,170,"SQLiteSaver","Aynı thread_id ile durum korunur.",true)
      + text(904,635,"Yeniden başlat → aynı incelemeye devam",25,color.teal,600);
    return card(72,500,660,180,"Onay → publish","Command(resume={approved: true, ...})",true)
      + text(96,640,"UNIQUE(run_id) · yinelenen raporu engeller",24,color.teal)
      + card(800,500,728,180,"Ret → end","Command(resume={approved: false, ...})")
      + text(824,640,"Rapor yayımlanmaz; iş rejected olur.",24,color.rose);
  }
  function pdfInput(p) {
    return text(72,274,"İki giriş seçeneği: PDF veya doğrudan metin",25,color.teal,600)
      + card(72,320,390,150,"Yerel PDF","En fazla 5 MiB / 5 sayfa",true)
      + wire([480,395,570,395],true,p)
      + card(590,320,420,150,"MinerU 4.0.12","Basic · ONNX · CPU OCR",true)
      + wire([1030,395,1100,395],true,p)
      + card(1120,320,408,150,"Çıkarılmış metin","İnsan kontrolünden sonra incele")
      + box(72,530,1456,155,"#f8fafb")
      + text(100,579,"PDF hash'i + sayfa sayısı + parser sürümü raporda korunur.",29,color.ink,600)
      + text(100,628,"Alıntılar çıkarılan metne göre doğrulanır. OCR hatalarını özgün PDF'den kontrol et.",26,color.muted);
  }
  function harness(stage,p) {
    let svg = box(72,258,1456,438,"#faf8fd","#e1d8ec")
      + text(100,300,"Harness² · İzole deney alanı",25,color.purple,600);
    if(stage===5) {
      svg += card(110,340,390,140,"Geliştirme belgeleri","İki kurgu örnek",true,color.purple)
        + wire([515,410,590,410],true,p,color.purple)
        + card(610,340,400,140,"Harness² çekirdeği","Propose → Probe → Compose",true,color.purple)
        + wire([1025,410,1100,410],true,p,color.purple)
        + card(1120,340,370,140,"Belge adaptörü","Adayı graph üzerinde çalıştır")
        + text(120,546,"Propose: izinli prompt adayı",26,color.purple,600)
        + text(120,594,"Probe: adayın gerçek yürütmesi",26,color.ink)
        + text(120,642,"Compose: seçilen değişikliklerin birleştirilmesi",26,color.ink)
        + card(1010,535,480,130,"ScriptedEditor","Önceden tanımlı profil değişimi");
    } else {
      svg += card(110,340,390,140,"DocumentAdapter","execute(task, harness, run_id)",true,color.purple)
        + wire([515,410,590,410],true,p,color.purple)
        + card(610,340,400,140,"Yeni LangGraph","read → review → verify → approval",true,color.purple)
        + wire([1025,410,1100,410],true,p,color.purple)
        + card(1120,340,370,140,"Kanıt + işlem izleri","publish adımına geçilmez")
        + `<path d="M1300 495V535H810V495" fill="none" stroke="${color.purple}" stroke-width="3" marker-end="url(#arrowActive)"/>`
        + text(120,590,"Seçim + reflection kayıtları",28,color.purple,600)
        + text(120,636,"Sonuçlar deney çıktısıdır; otomatik canlıya geçiş yok.",25,color.muted)
        + card(1010,560,480,112,"Ayrı holdout değerlendirmesi","Dört kurgu belge · adaptasyona girmez");
    }
    return svg;
  }
  function replay(p) {
    return card(72,320,420,155,"Yerel yürütmeler","Gerçek graph ve deney kayıtları",true)
      + wire([510,399,580,399],true,p)
      + card(600,320,390,155,"replay.json","Statik sonuç dosyası",true)
      + wire([1010,399,1080,399],true,p)
      + card(1100,320,428,155,"GitHub Pages","Etkileşimli kayıt oynatımı",true)
      + box(72,535,1456,150,"#f8fafb")
      + text(105,582,"Tarayıcı: kaynak inceleme, geçici onay / ret, JSON indirme",29,color.ink,600)
      + text(105,630,"Canlı model veya Python backend yok. Yeni işler yerel uygulamada çalışır.",27,color.muted);
  }
  let position=0, playing=false, started=0, raf=0, lastScene=-1;
  const chapterButtons = scenes.map(([label],i) => {
    const button=document.createElement("button");
    button.type="button"; button.textContent=`${i+1}. ${label}`;
    button.addEventListener("click",()=>seek(i*sceneLength));
    $("chapters").append(button); return button;
  });
  function render(ms) {
    position=Math.max(0,Math.min(duration,ms));
    const stage=Math.min(7,Math.floor(position/sceneLength));
    const p=(position%sceneLength)/sceneLength;
    const [,title,subtitle,caption]=scenes[stage];
    const accent=stage===5||stage===6?color.purple:color.teal;
    $("film").innerHTML=`<title id="film-title">${esc(title)}</title><desc id="film-description">${esc(subtitle+' '+caption)}</desc>
      <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10" fill="#bdcfd6"/></marker><marker id="arrowActive" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10" fill="${accent}"/></marker></defs>
      <rect width="1600" height="900" fill="white"/>
      ${text(72,75,"Tracework",35,color.ink,600)}${text(1528,75,`${stage+1} / 8`,25,color.muted,400,"end")}
      <line x1="72" y1="104" x2="1528" y2="104" stroke="${color.line}" stroke-width="2"/>
      ${text(72,174,title,45,color.ink,600)}${text(72,222,subtitle,26,color.muted)}
      ${stage===0?pdfInput(p):stage<5?reviewGraph(stage,p)+reviewDetail(stage,p):stage<7?harness(stage,p):replay(p)}
      <line x1="72" y1="737" x2="1528" y2="737" stroke="${color.line}" stroke-width="2"/>
      ${text(72,788,caption,26,color.ink)}
      ${text(72,846,"LangGraph + Harness² · Bağımsız, açık kaynak belge inceleme demosu",22,color.muted)}
      ${text(1528,846,"github.com/IbrahimSabriOrene/tracework-agent-lab",19,color.muted,400,"end")}
      <rect y="891" width="1600" height="9" fill="#edf2f4"/><rect y="891" width="${1600*position/duration}" height="9" fill="${accent}"/>`;
    $("timeline").value=position;
    $("time").textContent=`00:${String(Math.floor(position/1000)).padStart(2,"0")} / 00:48`;
    if(stage!==lastScene) {
      $("scene-description").textContent=title+" "+subtitle+" "+caption;
      chapterButtons.forEach((button,i)=>i===stage?button.setAttribute("aria-current","step"):button.removeAttribute("aria-current"));
      lastScene=stage;
    }
  }
  function pause() {
    playing=false; cancelAnimationFrame(raf);
    $("play").textContent="Oynat"; $("play").setAttribute("aria-label","Animasyonu oynat");
  }
  function seek(ms) { pause(); render(ms); }
  function tick(now) {
    if(!playing)return;
    render(now-started);
    if(position>=duration)pause(); else raf=requestAnimationFrame(tick);
  }
  function play() {
    if(position>=duration)position=0;
    playing=true; started=performance.now()-position;
    $("play").textContent="Duraklat"; $("play").setAttribute("aria-label","Animasyonu duraklat");
    raf=requestAnimationFrame(tick);
  }
  $("play").addEventListener("click",()=>playing?pause():play());
  $("restart").addEventListener("click",()=>seek(0));
  $("timeline").addEventListener("input",(event)=>seek(Number(event.target.value)));
  document.addEventListener("visibilitychange",()=>{if(document.hidden)pause();});
  window.traceworkAnimation={duration,seek,pause,play,get position(){return position;},get playing(){return playing;}};
  render(0);
  if(new URLSearchParams(location.search).has("autoplay")&&!matchMedia("(prefers-reduced-motion: reduce)").matches)play();
})();
