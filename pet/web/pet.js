/* MEKA · Companion Avatar & comunicación híbrida con el agente. Sin dependencias.
 *
 * - Inspirado en Soul-of-Waifu y docs/FILOSOFIA_HIBRIDA.md: identidad independiente del modelo
 *   con avatares intercambiables (Pixel Art animado ultraligero o stickers HD).
 * - Sin barras de estado vital punitivas: enfoque limpio en conversación, reacciones y presencia.
 * - Barra lateral oculta desplegable (Navigation Drawer con popover="manual" y scroll-snap).
 * - Comunicación en tiempo real con MEKA Core (WebSocket /v1/events + REST /v1/health).
 */
(() => {
  "use strict";

  const CATALOG = window.MEKA_SKINS;
  const STORAGE_KEY = "meka.companion.v2";
  const hasNativeHost = () =>
    typeof window.mekaStartDrag === "function" || Boolean(window.MEKA_NATIVE);
  const params = new URLSearchParams(location.search);
  const IS_DESKTOP = hasNativeHost() || params.has("desktop");
  const DEFAULT_CORE_URL = "ws://127.0.0.1:8765/v1/events";

  const FX = {
    idle:      { motion: "breathe",  label: "Stand By" },
    standby:   { motion: "breathe",  label: "Stand By" },
    greet:     { motion: "sway",     label: "Saludando",    particle: "👋",   miniParticle: "👋",    miniEvery: 1200, every: 1100, duration: 4500 },
    happy:     { motion: "bounce",   label: "Feliz",        particle: "💖",   miniParticle: "heart", miniEvery: 1050, every: 1000, duration: 4200 },
    love:      { motion: "love",     label: "Amorosa 💖",   particle: "💖",   miniParticle: "heart", miniEvery: 950,  every: 950,  duration: 5500 },
    sigh:      { motion: "sigh",     label: "Suspirando",   particle: "💨",   miniParticle: "💨",    miniEvery: 1400, every: 1400, duration: 4600 },
    surprise:  { motion: "surprise", label: "Sorpresa",     particle: "❗",   miniParticle: "❗",    miniEvery: 1050, every: 1000, duration: 4200 },
    excited:   { motion: "excited",  label: "Emocionada 🤩", particle: "🌟",  miniParticle: "🌟",    miniEvery: 850,  every: 850,  duration: 4800 },
    shy:       { motion: "shy",      label: "Tímida 🌸",    particle: "🌸",   miniParticle: "🌸",    miniEvery: 1100, every: 1100, duration: 4800 },
    chill:     { motion: "chill",    label: "Relajada ☕",  particle: "☕",   miniParticle: "☕",    miniEvery: 1350, every: 1350, duration: 5200 },
    curious:   { motion: "curious",  label: "Curiosa 🔍",   particle: "❔",   miniParticle: "❔",    miniEvery: 1150, every: 1150, duration: 4600 },
    proud:     { motion: "proud",    label: "Orgullosa 🏆", particle: "🏆",   miniParticle: "✨",    miniEvery: 950,  every: 950,  duration: 4800 },
    dance:     { motion: "dance",    label: "Bailando",     particle: "🎶",   miniParticle: "🎶",    miniEvery: 1000, every: 1100, duration: 5000 },
    working:   { motion: "sway",     label: "Trabajando",   particle: "⚡",   miniParticle: "⚡",    miniEvery: 1300, every: 1500 },
    thinking:  { motion: "tilt",     label: "Pensando",     particle: "💭",   miniParticle: "💭",    miniEvery: 1500, every: 1800, duration: 6500 },
    sleeping:  { motion: "sleep",    label: "En reposo",    particle: "z",    miniParticle: "z",     miniEvery: 1050, every: 1150, dim: true },
    yawn:      { motion: "yawn",     label: "Bostezando 🥱", particle: "💤",  miniParticle: "z",     miniEvery: 1300, every: 1500, duration: 3800 },
    charging:  { motion: "charging", label: "Cargando ⚡",  particle: "⚡",   miniParticle: "⚡",    miniEvery: 950,  every: 900,  duration: 4200 },
    gaming:    { motion: "gaming",   label: "Modo Gaming 🎮", particle: "🎮", miniParticle: "🎮",    miniEvery: 1300, every: 1400, duration: 6000 },
    focus:     { motion: "focus",    label: "Concentrada 🎯", particle: "🎯", miniParticle: "🎯",    miniEvery: 1400, every: 1500, duration: 6000 },
    dizzy:     { motion: "dizzy",    label: "Mareada 💫",   particle: "💫",   miniParticle: "💫",    miniEvery: 1100, every: 1100, duration: 4500 },
    eating:    { motion: "munch",    label: "Recargando",   particle: "food", miniParticle: "✨",    miniEvery: 1100, every: 900,  duration: 3800 },
    error:     { motion: "shake",    label: "Alerta",       particle: "💦",   miniParticle: "💦",    miniEvery: 1000, every: 950,  duration: 3800 },
    celebrate: { motion: "jump",     label: "Completado",   particle: "✨",   miniParticle: "✨",    miniEvery: 950,  every: 850,  duration: 4200 },
    sad:       { motion: "droop",    label: "Triste",       particle: "💧",   miniParticle: "💧",    miniEvery: 1300, every: 1300, duration: 4500 },
  };

  const SAMPLE_EVENTS = [
    ["📂 Trabajando", { type: "agent.working", data: { task: "Organizando repositorio" } }],
    ["✅ Completado", { type: "agent.done", data: { summary: "Tarea finalizada con éxito ✨" } }],
    ["🤔 Pensando", { type: "emotion", data: { emotion: "thinking" } }],
    ["🔐 Autorizar", { type: "agent.confirm", data: { id: "demo-1", action: "aplicar cambios en archivos" } }],
    ["💬 Mensaje", { type: "message", data: { text: "¡Sistemas sincronizados con MEKA Core!", emotion: "happy" } }],
    ["❌ Error", { type: "agent.error", data: { message: "El proveedor tardó en responder" } }],
    ["💸 Límite API", { type: "budget.low", data: {} }],
    ["🔔 Notificación", { type: "system.notification", data: { id: 1, app: "Telegram", title: "Meka Dev", body: "Reunión técnica One UI 9" } }],
    ["🎵 Multimedia", { type: "system.media", data: { playing: true, title: "Starboy", artist: "The Weeknd", app: "Spotify", position: 32, duration: 230 } }],
    ["🎯 Concentración", { type: "focus.started", data: { until: Math.floor(Date.now() / 1000) + 14400, minutes: 240 } }],
    ["⏹ Fin Focus", { type: "focus.ended", data: { reason: "user", held: 3, notifications: 2 } }],
    ["⏰ Recordatorio", { type: "reminder.due", data: { id: 1, title: "Revisar despliegue", text: "⏰ Te recuerdo: Revisar despliegue" } }],
    ["💡 Proactiva", { type: "nudge", data: { text: "Tienes 2 tareas pendientes para hoy ✨", kind: "tasks", tasks: 2, overdue: 0, notifications: 0 } }],
  ];

  // ------------------------------------------------------------------ utilidades y transiciones

  const $ = (id) => document.getElementById(id);
  const pick = (list) => list[Math.floor(Math.random() * list.length)];

  let supportsDisplayTransition;
  function canTransitionDisplay() {
    if (supportsDisplayTransition !== undefined) return supportsDisplayTransition;
    if (!window.CSS?.supports?.("transition-behavior", "allow-discrete") || !document.body) {
      return false;
    }
    const probe = document.createElement("div");
    probe.style.cssText = "transition: display 1s allow-discrete !important; display: block;";
    document.body.appendChild(probe);
    getComputedStyle(probe).display;
    probe.style.display = "none";
    supportsDisplayTransition = getComputedStyle(probe).display === "block";
    probe.remove();
    return supportsDisplayTransition;
  }

  function showElement(el) {
    if (!el) return;
    el.removeAttribute("data-closing");
    el.hidden = false;
  }

  async function hideElement(el) {
    if (!el || el.hidden) return;
    if (canTransitionDisplay()) {
      el.hidden = true;
    } else {
      el.setAttribute("data-closing", "");
    }
    const animations = el.getAnimations ? el.getAnimations() : [];
    if (animations.length > 0) {
      await Promise.race([
        Promise.allSettled(animations.map((a) => a.finished)),
        new Promise((r) => setTimeout(r, 350)),
      ]);
    }
    if (el.hasAttribute("data-closing")) {
      el.removeAttribute("data-closing");
      el.hidden = true;
    }
  }

  const els = {
    mainDesk: $("mainDesk"),
    stage: $("stage"),
    stageTop: $("stageTop"),
    headerBattery: $("headerBattery"),
    focusBadge: $("focusBadge"),
    focusTimerText: $("focusTimerText"),
    focusToggleBtn: $("focusToggleBtn"),
    focusCardSwitchBtn: $("focusCardSwitchBtn"),
    focusCardSwitchLabel: $("focusCardSwitchLabel"),
    glassToggleBtn: $("glassToggleBtn"),
    focusSummaryText: $("focusSummaryText"),
    stageFocusCard: $("stageFocusCard"),
    stageHero: $("stageHero"),
    stageShelf: $("stageShelf"),
    stageSkinsCard: $("stageSkinsCard"),
    skinsCloseBtn: $("skinsCloseBtn"),
    proactiveBanner: $("proactiveBanner"),
    proactiveBannerIcon: $("proactiveBannerIcon"),
    proactiveBannerKicker: $("proactiveBannerKicker"),
    proactiveBannerTitle: $("proactiveBannerTitle"),
    proactiveBannerActions: $("proactiveBannerActions"),
    proactiveDoneBtn: $("proactiveDoneBtn"),
    proactiveSnoozeBtn: $("proactiveSnoozeBtn"),
    proactiveCloseBtn: $("proactiveCloseBtn"),
    proactiveAskBtn: $("proactiveAskBtn"),
    proactiveTasksSection: $("proactiveTasksSection"),
    taskCountBadge: $("taskCountBadge"),
    stageTaskList: $("stageTaskList"),
    notifScrollArea: $("notifScrollArea"),
    drawer: $("drawer"),
    drawerOpen: $("drawer-open"),
    drawerClose: $("drawer-close"),
    skinBadge: $("skinBadge"),
    miniThumb: $("miniThumb"),
    miniParticles: $("miniParticles"),
    expandHint: $("expandHint"),
    // Samsung Brief & One UI 9
    briefDots: $("briefDots"),
    briefViewport: $("briefViewport"),
    briefTrack: $("briefTrack"),
    briefAvatar: $("briefAvatar"),
    briefMedia: $("briefMedia"),
    briefNotif: $("briefNotif"),
    briefNotifIcon: $("briefNotifIcon"),
    briefNotifBrand: $("briefNotifBrand"),
    briefNotifEmoji: $("briefNotifEmoji"),
    briefNotifSvg: $("briefNotifSvg"),
    briefMediaTitle: $("briefMediaTitle"),
    briefMediaArtist: $("briefMediaArtist"),
    briefWaveform: $("briefWaveform"),
    briefNotifTitle: $("briefNotifTitle"),
    briefNotifSubtitle: $("briefNotifSubtitle"),
    briefNotifDot: $("briefNotifDot"),
    stageNotifCard: $("stageNotifCard"),
    stageNotifList: $("stageNotifList"),
    stageNotifEmpty: $("stageNotifEmpty"),
    notifCountBadge: $("notifCountBadge"),
    notifClearAllBtn: $("notifClearAllBtn"),
    heroMoodBar: $("heroMoodBar"),
    pet: $("pet"),
    body: $("petBody"),
    img: $("petImg") || $("sprite"),
    pixel: $("pixelSprite"),
    particles: $("particles"),
    bubble: $("bubble"),
    bubbleSpeaker: $("bubbleSpeaker"),
    bubbleTag: $("bubbleTag"),
    bubbleText: $("bubbleText"),
    confirmBar: $("confirmBar"),
    confirmApprove: $("confirmApprove"),
    confirmReject: $("confirmReject"),
    skinNameLabel: $("skinNameLabel"),
    stateLabel: $("stateLabel"),
    menuBtn: $("menuBtn"),
    menu: $("menu"),
    chatForm: $("chatForm") || $("promptForm"),
    chatInput: $("chatInput") || $("promptInput"),
    promptForm: $("promptForm") || $("chatForm"),
    promptInput: $("promptInput") || $("chatInput"),
    promptMic: $("promptMic"),
    promptSend: $("promptSend"),
    styleToggleBtn: $("styleToggleBtn"),
    popoutBtn: $("popoutBtn"),
    themeToggle: $("themeToggle"),
    styleIndicator: $("styleIndicator"),
    skinCards: $("skinCards"),
    coreBadge: $("coreBadge"),
    coreToken: $("coreToken"),
    coreHealthInfo: $("coreHealthInfo"),
    eventLog: $("eventLog"),
    clearLog: $("clearLog"),
    hudCoreDot: $("hudCoreDot"),
    hudCoreText: $("hudCoreText"),
    hudMoodIcon: $("hudMoodIcon"),
    hudMoodText: $("hudMoodText"),
    hudSkinText: $("hudSkinText"),
    miniMusicBar: $("miniMusicBar"),
    hudBatteryChip: $("hudBatteryChip"),
    hudBatteryIcon: $("hudBatteryIcon"),
    hudBatteryText: $("hudBatteryText"),
    mediaWidget: $("mediaWidget"),
    mediaSource: $("mediaSource") || $("mediaApp"),
    mediaApp: $("mediaApp") || $("mediaSource"),
    mediaOutputBtn: $("mediaOutputBtn"),
    mediaTitle: $("mediaTitle"),
    mediaDot: $("mediaDot"),
    mediaArtist: $("mediaArtist"),
    mediaBarFill: $("mediaBarFill"),
    mediaBarOrb: $("mediaBarOrb"),
    mediaTime: $("mediaTime"),
    mediaTimeCurrent: $("mediaTimeCurrent"),
    mediaTimeTotal: $("mediaTimeTotal"),
    mediaLikeBtn: $("mediaLikeBtn"),
    mediaPrev: $("mediaPrev"),
    mediaPlayPause: $("mediaPlayPause"),
    mediaNext: $("mediaNext"),
    mediaShuffleBtn: $("mediaShuffleBtn"),
    hudActionGreet: $("hudActionGreet"),
    hudActionSleep: $("hudActionSleep"),
    hudActionSleepIcon: $("hudActionSleepIcon"),
    hudActionSleepLabel: $("hudActionSleepLabel"),
    hudActionStyle: $("hudActionStyle"),
    hudActionStyleLabel: $("hudActionStyleLabel"),
    hudActionSkins: $("hudActionSkins"),
    stageGlassCoverBlur: $("stageGlassCoverBlur"),
    stageSettingsCard: $("stageSettingsCard"),
    settingsCloseBtn: $("settingsCloseBtn"),
    settingsScrollArea: $("settingsScrollArea"),
    privateToggleBtn: $("privateToggleBtn"),
    sleepToggleBtn: $("sleepToggleBtn"),
    settingsProactiveBtn: $("settingsProactiveBtn"),
    settingsCenterBtn: $("settingsCenterBtn"),
    settingsDodgeBtn: $("settingsDodgeBtn"),
    settingsScreenshotBtn: $("settingsScreenshotBtn"),
    closeAppBtn: $("closeAppBtn"),
    topCloseAppBtn: $("topCloseAppBtn"),
    autoExpandToggleBtn: $("autoExpandToggleBtn"),
    winEventsToggleBtn: $("winEventsToggleBtn"),
    autoStartToggleBtn: $("autoStartToggleBtn"),
    coreRunsSummary: $("coreRunsSummary"),
    coreResetSessionBtn: $("coreResetSessionBtn"),
    taskQuickForm: $("taskQuickForm"),
    taskQuickInput: $("taskQuickInput"),
    agentReplyDock: $("agentReplyDock"),
    agentDockSpeaker: $("agentDockSpeaker"),
    agentDockBadge: $("agentDockBadge"),
    agentDockMeta: $("agentDockMeta"),
    agentDockBody: $("agentDockBody"),
    agentDockText: $("agentDockText"),
    briefMediaCover: $("briefMediaCover"),
    briefMediaIcon: $("briefMediaIcon"),
    mediaCoverBackdropImg: $("mediaCoverBackdropImg"),
    mediaArtworkWrap: $("mediaArtworkWrap"),
    mediaCoverImg: $("mediaCoverImg"),
    mediaDiscIcon: $("mediaDiscIcon"),
    mediaProgressNative: $("mediaProgressNative"),
    mediaAlbum: $("mediaAlbum"),
  };

  // ------------------------------------------------------------------ estado persistente

  function defaults() {
    return {
      skin: "hana",
      style: "anime",
      theme: "dark",
      glass: "liquid",
      sleeping: false,
      privateMode: false,
      autoExpandEvents: false,
      winEventsEnabled: true,
    };
  }

  function load() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (saved && typeof saved === "object") {
        const glass = saved.glass === "normal" ? "normal" : "liquid";
        // Ignora autoExpandEvents de sesiones antiguas salvo toggle manual explícito
        const autoExpandEvents = saved.autoExpandManual === true
          ? Boolean(saved.autoExpandEvents)
          : false;
        const winEventsEnabled = typeof saved.winEventsEnabled === "boolean"
          ? saved.winEventsEnabled
          : true;
        return { ...defaults(), ...saved, glass, autoExpandEvents, winEventsEnabled, style: "anime" };
      }
    } catch {
      /* Almacenamiento no disponible */
    }
    return defaults();
  }

  function save(nextState) {
    if (nextState && typeof nextState === "object") {
      Object.assign(pet, nextState);
    }
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(pet));
    } catch {
      /* Modo privado */
    }
  }

  const pet = load();
  if (!CATALOG?.skins?.[pet.skin]) {
    pet.skin = CATALOG?.skins?.[CATALOG?.default] ? CATALOG.default : "hana";
    save();
  }
  pet.style = "anime";

  // ------------------------------------------------------------------ estado en ejecución

  let base = pet.sleeping ? "sleeping" : "idle";
  let current = base;
  let agentWorking = false;
  let pendingConfirmId = null;
  let pendingDockQueue = [];
  let dockUpdateSeq = 0;
  let transientTimer = null;
  let particleTimer = null;
  let particleSeq = 0;
  let miniParticleTimer = null;
  let miniParticleSeq = 0;
  let bubbleTimer = null;
  let typeTimer = null;
  let lastPet = 0;
  let inactivityTimer = null;
  let isAutoSleeping = false;
  let isMusicReactivity = false;
  let musicActiveLabel = null;
  let transientEventTimer = null;
  let transientEventAction = null;
  let islandPulseTimer = null;
  let mediaGlowTimer = null;
  let islandPulsePreviewText = null;
  let petClickMoodIndex = 0;
  let hasDockMessage = false;
  let focusActive = false;
  let focusUntil = null;
  let focusInterval = null;
  let focusRenewTimer = null;
  let lastFocusToggleAt = 0;
  const FOCUS_RENEW_MS = 180 * 60 * 1000;
  const proactiveUser = new URLSearchParams(window.location.search).get("user") || "me";
  let pendingTasks = [];
  let activeProactiveAlert = null;
  let momentaryExpandTimer = null;
  let momentaryCollapseAt = 0;
  let wasCollapsedBeforeMomentary = false;
  const INACTIVITY_DELAY_MS = 60_000;
  const NATIVE_IDLE_FRESH_MS = 75_000;
  const YAWN_DURATION_MS = 3500;
  let lastNativeIdleAt = 0;
  let localYawnTimer = null;
  let isLocalYawning = false;
  let tempBodyMotionTimer = null;
  let activeTempBodyMotion = null;
  let lastPowerPlugged = null;
  let lastPowerLowOrSaver = false;
  let activeWindowsContext = "normal";
  let lastNetworkOnline = null;
  let lastVolumePercent = null;
  let lastVolumeMuted = null;
  let petDoubleClickToggle = false;
  let heightUpdateRafId = null;

  const core = {
    ws: null,
    connected: false,
    offline: false,
    retry: 1000,
    timer: null,
    url: DEFAULT_CORE_URL,
    token: "",
  };
  core.send = (message) => {
    if (core.connected && core.ws) core.ws.send(JSON.stringify(message));
  };

  function reportCoreFetchError(endpoint, err) {
    console.warn(`[MEKA] Error al consultar ${endpoint}:`, err);
    if (!core.connected) {
      core.offline = true;
      const el = $("coreStatus");
      if (el) el.textContent = "desconectado";
      if (els.coreBadge) els.coreBadge.dataset.connected = "false";
      if (els.hudCoreText) els.hudCoreText.textContent = "Core desconectado";
      if (els.hudCoreDot) {
        els.hudCoreDot.style.background = "#ff453a";
        els.hudCoreDot.style.boxShadow = "0 0 6px #ff453a";
      }
      if (typeof updateStageBadges === "function") {
        updateStageBadges();
      }
    }
  }

  function coreHttpConfig(wsUrlOverride, tokenOverride) {
    try {
      const rawUrl =
        wsUrlOverride ||
        core.url ||
        params.get("core") ||
        ($("coreUrl") ? $("coreUrl").value.trim() : "") ||
        DEFAULT_CORE_URL;
      const u = new URL(rawUrl);
      const httpProto = u.protocol === "wss:" ? "https:" : "http:";
      const token =
        tokenOverride !== undefined
          ? tokenOverride
          : core.token || params.get("token") || (els.coreToken ? els.coreToken.value.trim() : "");
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      return { baseUrl: `${httpProto}//${u.host}`, headers, token };
    } catch {
      return null;
    }
  }

  const skin = () =>
    CATALOG?.skins?.[pet.skin] ||
    CATALOG?.skins?.[CATALOG?.default] ||
    CATALOG?.skins?.hana ||
    Object.values(CATALOG?.skins || {})[0];
  const getCleanAvatarName = (sk = skin()) => {
    const raw = sk?.name || "";
    return raw.split(" · ")[0].trim() || raw;
  };
  const LINE_FALLBACKS = {
    love: "happy",
    yawn: "sleeping",
    charging: "happy",
    gaming: "working",
    focus: "thinking",
    dizzy: "error",
  };
  const line = (kind) =>
    pick(
      skin().lines[kind] ||
      (LINE_FALLBACKS[kind] ? skin().lines[LINE_FALLBACKS[kind]] : null) ||
      skin().lines.idle
    );

  const EMOTION_ALIASES = {
    idle: "idle",
    ready: "idle",
    online: "idle",
    standby: "standby",
    "stand-by": "standby",
    stand_by: "standby",
    calm: "standby",
    neutral: "standby",
    greet: "greet",
    greeting: "greet",
    wave: "greet",
    hello: "greet",
    hi: "greet",
    welcome: "greet",
    happy: "happy",
    joy: "happy",
    love: "love",
    amor: "love",
    corazon: "love",
    corazón: "love",
    affection: "love",
    heart: "love",
    adore: "love",
    cariño: "love",
    surprise: "surprise",
    surprised: "surprise",
    shock: "surprise",
    shocked: "surprise",
    alert: "surprise",
    amazed: "surprise",
    wow: "surprise",
    dance: "dance",
    dancing: "dance",
    music: "dance",
    groove: "dance",
    working: "working",
    work: "working",
    busy: "working",
    thinking: "thinking",
    think: "thinking",
    curious: "curious",
    curiosa: "curious",
    duda: "curious",
    wonder: "curious",
    sleeping: "sleeping",
    sleep: "sleeping",
    nap: "sleeping",
    afk: "sleeping",
    yawn: "yawn",
    yawning: "yawn",
    bostezo: "yawn",
    bostezando: "yawn",
    sleepy: "yawn",
    soñolienta: "yawn",
    charging: "charging",
    charge: "charging",
    cargando: "charging",
    plugged: "charging",
    gaming: "gaming",
    game: "gaming",
    gamer: "gaming",
    jugando: "gaming",
    focus: "focus",
    focused: "focus",
    concentracion: "focus",
    concentración: "focus",
    concentrada: "focus",
    coding: "focus",
    dizzy: "dizzy",
    mareo: "dizzy",
    mareada: "dizzy",
    confused: "dizzy",
    offline: "dizzy",
    eating: "eating",
    eat: "eating",
    snack: "eating",
    error: "error",
    fail: "error",
    failed: "error",
    warning: "error",
    celebrate: "celebrate",
    celebration: "celebrate",
    victory: "celebrate",
    proud: "proud",
    orgullosa: "proud",
    orgullo: "proud",
    excited: "excited",
    emocionada: "excited",
    hype: "excited",
    shy: "shy",
    timida: "shy",
    tímida: "shy",
    blush: "shy",
    sonrojada: "shy",
    chill: "chill",
    relajada: "chill",
    relax: "chill",
    serena: "chill",
    sad: "sad",
    unhappy: "sad",
    sigh: "sigh",
    suspiro: "sigh",
    cansada: "sigh",
    exhausted: "sigh",
    tired: "sigh",
    sorry: "sad",
  };

  function inferEmotionFromText(text = "") {
    const t = String(text || "").trim();
    if (!t) return null;
    if (/\b(?:te quiero|te amo|amor|cariñ[oa]|adoro)\b|❤️|💖|💕|💗/i.test(t)) {
      return "love";
    }
    if (/\b(?:qué emoción|increíble|genial|hype|épico|wow)\b|🤩|🌟/i.test(t)) {
      return "excited";
    }
    if (/\b(?:orgullos[oa]|logrado|impecable|medalla)\b|🏆/i.test(t)) {
      return "proud";
    }
    if (/\b(?:me da pena|da pena|penita|t[ií]mid[oa]|avergonzad[oa]|sonrojad[oa])\b|😳|🌸/i.test(t)) {
      return "shy";
    }
    if (/\b(?:curios[oa]|hmm+|qué ser[aá]|interesante)\b|🔍/i.test(t)) {
      return "curious";
    }
    if (/\b(?:relajad[oa]|chill|tranquil[oa]|caf[eé]|t[eé] verde|taza de t[eé]|infusi[oó]n)\b|☕/i.test(t)) {
      return "chill";
    }
    if (/\b(?:bostez[oa]|bostezando|sueñ[oa]|soñolient[oa])\b|🥱/i.test(t)) {
      return "yawn";
    }
    if (/\b(?:cargando|cargador|enchufad[oa]|recargando bater[ií]a)\b|🔌|🔋⚡/i.test(t)) {
      return "charging";
    }
    if (/\b(?:modo gaming|gaming|gamer|jugando|videojuego)\b|🎮|🕹️/i.test(t)) {
      return "gaming";
    }
    if (/\b(?:concentrad[oa]|concentraci[oó]n|enfoque|modo focus|programando|estudiando)\b|🎯/i.test(t)) {
      return "focus";
    }
    if (/\b(?:maread[oa]|mareo|aturdid[oa]|sin conexi[oó]n|desconectad[oa])\b|💫|😵‍💫/i.test(t)) {
      return "dizzy";
    }
    if (/\b(?:suspir[oa]|cansad[oa]|fiu+|exhaust[oa])\b|😮‍💨/i.test(t)) {
      return "sigh";
    }
    if (/¡¿|¿!|¡\?|!\?|\bsorpres(?:a|ivo|iva)\b|\binesperad[oa]s?\b/i.test(t)) {
      return "surprise";
    }
    if (/\btriste(?:za)?\b|\blamento\b|\blo siento\b/i.test(t)) {
      return "sad";
    }
    return null;
  }

  function normalizeEmotion(raw, text = "") {
    const key = String(raw || "").trim().toLowerCase();
    const mapped = key ? (Object.hasOwn(FX, key) ? key : (EMOTION_ALIASES[key] || null)) : null;
    const inferred = inferEmotionFromText(text);
    if (inferred && (!mapped || mapped === "idle" || mapped === "happy")) {
      return inferred;
    }
    if (mapped) return mapped;
    return null;
  }

  const validState = (name, text = "") => normalizeEmotion(name, text);

  function logActivity(tag, detail = "") {
    if (!els.eventLog) return;
    const li = document.createElement("li");
    const time = document.createElement("time");
    time.textContent = new Date().toTimeString().slice(0, 8);
    const code = document.createElement("code");
    code.textContent = tag;
    const span = document.createElement("span");
    span.textContent = detail;
    li.append(time, code, span);
    els.eventLog.prepend(li);
    while (els.eventLog.children.length > 25) {
      els.eventLog.lastElementChild.remove();
    }
  }

  // ------------------------------------------------------------------ Selector de Personajes y Gestión de Vistas Exclusivas

  let skinsCardOpen = false;
  let stageView = "hero"; // 'hero' | 'skins' | 'notifs' | 'media'

  function briefToStageView(brief) {
    switch (brief) {
      case "media": return "media";
      case "notif": return "notifs";
      case "avatar":
      default:
        return "hero";
    }
  }

  function setStageView(view) {
    if (!["hero", "media", "notifs", "skins", "focus", "settings"].includes(view)) {
      view = "hero";
    }
    stageView = view;
    if (els.stage) {
      els.stage.setAttribute("data-stage-view", view);
    }
    if (els.stageShelf) {
      els.stageShelf.setAttribute("data-stage-view", view);
    }

    skinsCardOpen = (view === "skins");
    els.stage?.classList.toggle("has-skins-open", skinsCardOpen);

    // Mutua exclusión gobernada por la vista activa
    if (els.stageSkinsCard) els.stageSkinsCard.hidden = (view !== "skins");
    if (els.stageHero) els.stageHero.hidden = (view !== "hero");
    if (els.stageNotifCard) els.stageNotifCard.hidden = (view !== "notifs");
    if (els.mediaWidget) els.mediaWidget.hidden = (view !== "media");
    if (els.stageFocusCard) els.stageFocusCard.hidden = (view !== "focus");
    if (els.stageSettingsCard) els.stageSettingsCard.hidden = (view !== "settings");

    if (view === "skins") {
      els.hudActionSkins?.classList.add("is-active");
      els.hudActionSkins?.setAttribute("aria-expanded", "true");
      els.drawerOpen?.setAttribute("aria-expanded", "true");
      renderSkinCards();
    } else {
      els.hudActionSkins?.classList.remove("is-active");
      els.hudActionSkins?.setAttribute("aria-expanded", "false");
      els.drawerOpen?.setAttribute("aria-expanded", "false");
    }

    if (els.menuBtn) {
      els.menuBtn.classList.toggle("is-active", view === "settings");
      els.menuBtn.setAttribute("aria-expanded", String(view === "settings"));
    }

    if (view === "settings" && core.connected && typeof fetchCoreDiagnosticsSummary === "function") {
      fetchCoreDiagnosticsSummary();
    }

    if (els.chatForm) {
      els.chatForm.hidden = !notchExpanded || (stageView !== "hero");
    }

    requestExpandedHeightUpdate();
  }

  function setSkinsCardOpen(open) {
    const shouldOpen = Boolean(open);
    if (!els.stage) return;

    if (shouldOpen) {
      if (!notchExpanded) {
        setNotchExpanded(true);
      }
      setStageView("skins");
    } else {
      setStageView(briefToStageView(activeBrief));
    }
  }

  function toggleSkinsCard() {
    setSkinsCardOpen(!skinsCardOpen);
  }

  function setSettingsCardOpen(open) {
    const shouldOpen = Boolean(open);
    if (!els.stage) return;
    if (shouldOpen) {
      if (!notchExpanded) {
        setNotchExpanded(true);
      }
      setStageView("settings");
    } else {
      setStageView("hero");
    }
  }

  function toggleSettingsCard() {
    setSettingsCardOpen(stageView !== "settings");
  }

  function setupSkinsSelector() {
    els.hudActionSkins?.addEventListener("click", (event) => {
      event.stopPropagation();
      toggleSkinsCard();
    });

    els.drawerOpen?.addEventListener("click", (event) => {
      event.stopPropagation();
      toggleSkinsCard();
    });

    els.skinsCloseBtn?.addEventListener("click", (event) => {
      event.stopPropagation();
      setSkinsCardOpen(false);
    });

    window.MEKA_DRAWER = {
      open: () => setSkinsCardOpen(true),
      close: () => setSkinsCardOpen(false),
      toggle: toggleSkinsCard,
    };
  }

  // ------------------------------------------------------------------ sprites y animación Chibi HD

  const SPRITE_FALLBACKS = {
    love: "happy",
    yawn: "sleeping",
    charging: "happy",
    gaming: "working",
    focus: "thinking",
    dizzy: "error",
  };

  function spriteFor(state) {
    const sk = skin();
    const keys =
      sk.states[state] ||
      (SPRITE_FALLBACKS[state] ? sk.states[SPRITE_FALLBACKS[state]] : null) ||
      sk.states.idle;
    const key = pick(keys);
    return sk.sprites[key] || sk.sprites.idle;
  }

  function setSprite(src) {
    const miniEl = els.miniThumb || $("miniThumb");
    if (miniEl && miniEl.getAttribute("src") !== src) miniEl.src = src;
    const imgEl = els.img || $("petImg") || $("sprite");
    if (imgEl && imgEl.getAttribute("src") !== src) imgEl.src = src;
    else renderPixel();
  }

  function preload(sk) {
    if (!sk || !sk.sprites) return;
    for (const src of Object.values(sk.sprites)) new Image().src = src;
  }

  function renderPixel() {
    const imgEl = els.img || $("petImg") || $("sprite");
    els.pet?.classList.add("is-smooth");
    els.stage?.classList.add("is-smooth");
    document.documentElement.dataset.style = "anime";
    if (imgEl) imgEl.hidden = false;
    if (els.pixel) els.pixel.hidden = true;
    if (els.styleIndicator) {
      els.styleIndicator.textContent = "Chibi HD";
    }
  }

  els.img?.addEventListener("load", renderPixel);

  // ------------------------------------------------------------------ máquina de estados del avatar

  function computeMoodLabel() {
    if (!notchExpanded && activeBrief === "avatar" && islandPulsePreviewText) {
      return islandPulsePreviewText;
    }
    const fx = FX[current] || FX.idle;
    const isOffline = !core.connected && core.offline;
    if (isOffline) return "Core desconectado";
    if (transientEventAction) return "Activo ✨";
    if (pet.sleeping || isAutoSleeping || current === "sleeping") {
      return pet.skin === "hana" ? "AFK · Zzz 😴" : "En reposo · Zzz 😴";
    }
    if (focusActive) return "Concentración 🎯";
    return fx.label;
  }

  function updateStageBadges() {
    const sk = skin();
    const fx = FX[current] || FX.idle;
    if (els.stage) els.stage.dataset.state = current;

    const cleanName = getCleanAvatarName(sk);
    const displayName = transientEventAction
      ? `${cleanName} · ${transientEventAction}`
      : cleanName;

    if (els.skinNameLabel) {
      els.skinNameLabel.textContent = displayName;
      els.skinNameLabel.setAttribute("data-raw-text", displayName);
    }
    if (els.bubbleSpeaker) els.bubbleSpeaker.textContent = cleanName;
    if (els.agentDockSpeaker) els.agentDockSpeaker.textContent = cleanName;

    const moodLabel = computeMoodLabel();

    const sleepSwitch = els.sleepToggleBtn || $("sleepToggleBtn");
    if (sleepSwitch) {
      const sleepingNow = Boolean(pet.sleeping || isAutoSleeping);
      sleepSwitch.classList.toggle("is-active", sleepingNow);
      sleepSwitch.setAttribute("aria-checked", String(sleepingNow));
    }

    if (els.stateLabel) {
      els.stateLabel.textContent = moodLabel;
      els.stateLabel.setAttribute("data-raw-text", moodLabel);
    }
    if (els.hudMoodText) els.hudMoodText.textContent = moodLabel;
    if (els.hudMoodIcon) els.hudMoodIcon.textContent = transientEventAction ? "✨" : (fx.particle || "💖");
    if (els.hudSkinText) els.hudSkinText.textContent = cleanName;
    if (els.hudActionSleepLabel) els.hudActionSleepLabel.textContent = pet.sleeping ? "Despertar" : "Reposo";
    if (els.hudActionSleepIcon) els.hudActionSleepIcon.textContent = pet.sleeping ? "☀️" : "😴";
    if (els.hudActionStyleLabel) els.hudActionStyleLabel.textContent = "Chibi HD";
    const moodBar = els.heroMoodBar || $("heroMoodBar");
    if (moodBar) {
      moodBar.querySelectorAll("button[data-mood]").forEach((btn) => {
        btn.classList.toggle("is-active", btn.dataset.mood === current);
      });
    }
    requestAnimationFrame(() => {
      if (els.skinNameLabel) checkAndApplyMarquee(els.skinNameLabel, { text: displayName });
      if (els.stateLabel) checkAndApplyMarquee(els.stateLabel, { text: moodLabel });
    });
    syncIslandIllumination({ animate: activeBrief === "avatar" });
  }

  function triggerTransientAvatarReaction({ actionText, mood = "happy", durationMs = 4500 }) {
    clearTimeout(transientEventTimer);
    clearTimeout(transientTimer);
    transientTimer = null;
    transientEventAction = actionText;

    if (pet.sleeping) {
      isAutoSleeping = false;
      pet.sleeping = false;
    }

    const resolvedMood = normalizeEmotion(mood) || "happy";
    const targetMood = (skin().states && skin().states[resolvedMood]) ? resolvedMood : "happy";
    show(targetMood);
    updateStageBadges();
    resetInactivityTimer();

    transientEventTimer = setTimeout(() => {
      transientEventAction = null;
      if (!agentWorking && !pet.sleeping) {
        show("idle");
        setBase("idle");
      }
      updateStageBadges();
    }, durationMs);
  }

  function clearTempBodyMotion({ restore = true } = {}) {
    clearTimeout(tempBodyMotionTimer);
    tempBodyMotionTimer = null;
    activeTempBodyMotion = null;
    if (restore && els.body) {
      const fx = FX[current] || FX.idle;
      els.body.dataset.motion = fx.motion;
    }
  }

  function triggerTempBodyMotion(motion, ms = 1800) {
    if (!els.body || !motion) return;
    clearTimeout(tempBodyMotionTimer);
    activeTempBodyMotion = motion;
    els.body.dataset.motion = motion;
    tempBodyMotionTimer = setTimeout(() => {
      tempBodyMotionTimer = null;
      activeTempBodyMotion = null;
      if (els.body) {
        const fx = FX[current] || FX.idle;
        els.body.dataset.motion = fx.motion;
      }
    }, Math.max(300, Number(ms) || 1800));
  }

  function show(state) {
    current = state;
    clearIslandSubtlePulse({ sync: false });
    clearTempBodyMotion({ restore: false });
    if (state === "sleeping") {
      clearTimeout(transientEventTimer);
      transientEventTimer = null;
      transientEventAction = null;
    }
    const fx = FX[state] || FX.idle;
    els.body.dataset.motion = fx.motion;
    els.pet.classList.toggle("is-dim", Boolean(fx.dim));
    const miniEl = els.miniThumb || $("miniThumb");
    if (miniEl) {
      miniEl.dataset.miniState = state;
    }
    setSprite(spriteFor(state));
    startParticles(fx.particle, fx.every);
    startMiniParticles(fx.miniParticle, fx.miniEvery);
    updateStageBadges();
  }

  function play(state, text, opts = {}) {
    const {
      particle,
      duration,
      confirmId,
      directToDock,
      dockTone,
      dockBadge,
      forceExpand,
      pulseState,
      pulseText,
      brandColor,
      brandColor2,
      skipPulse,
      suppressAutoExpand,
      keepCurrentBrief = false,
    } = opts || {};
    if (pet.sleeping && state !== "sleeping") wake({ quiet: true });
    clearTimeout(transientTimer);
    transientTimer = null;
    show(state);
    if (
      !notchExpanded &&
      activeBrief !== "avatar" &&
      !keepCurrentBrief &&
      userPinnedBrief !== "media" &&
      userPinnedBrief !== "notif"
    ) {
      clearTimeout(briefPreviewTimer);
      setActiveBrief("avatar", { syncView: false });
    }
    if (particle) startParticles(particle, (FX[state] || FX.idle).every || 900);
    const ms = duration ?? (FX[state] || FX.idle).duration;
    if (ms) {
      transientTimer = setTimeout(() => {
        transientTimer = null;
        show(base);
      }, ms);
    }
    if (text) {
      say(text, {
        duration: confirmId ? (duration ?? 120_000) : undefined,
        confirmId,
        directToDock,
        dockTone,
        dockBadge,
        forceExpand,
        pulseState: pulseState || state,
        pulseText,
        brandColor,
        brandColor2,
        skipPulse,
        suppressAutoExpand,
      });
    }
  }

  function setBase(state, { interrupt = false } = {}) {
    base = state;
    if (interrupt) {
      clearTimeout(transientTimer);
      transientTimer = null;
    }
    if (!transientTimer) show(state);
  }

  function setState(state) {
    play(validState(state) || "happy");
  }

  function sleep() {
    clearTimeout(localYawnTimer);
    localYawnTimer = null;
    isLocalYawning = false;
    isAutoSleeping = false;
    pet.sleeping = true;
    clearTimeout(transientTimer);
    transientTimer = null;
    setBase("sleeping");
    say(line("sleeping"), { suppressAutoExpand: true, pulseState: "sleeping", pulseText: "" });
    save();
  }

  function wake({ quiet = false } = {}) {
    clearTimeout(localYawnTimer);
    localYawnTimer = null;
    isLocalYawning = false;
    isAutoSleeping = false;
    pet.sleeping = false;
    setBase(agentWorking ? "working" : "idle");
    if (!quiet) say(line("wake"), { suppressAutoExpand: true, pulseState: "idle", pulseText: "" });
    save();
  }

  // ------------------------------------------------------------------ Living avatar: auto-sleep, interactividad y squash & stretch

  function scheduleInactivityTimer() {
    clearTimeout(inactivityTimer);
    inactivityTimer = setTimeout(() => {
      handleInactivityTimeout();
    }, INACTIVITY_DELAY_MS);
  }

  function enterAutoSleep() {
    clearTimeout(localYawnTimer);
    localYawnTimer = null;
    isLocalYawning = false;
    if (pet.sleeping) return;
    isAutoSleeping = true;
    pet.sleeping = true;
    clearTimeout(transientTimer);
    transientTimer = null;
    setBase("sleeping", { interrupt: true });
    show("sleeping");
    say(line("sleeping"), { suppressAutoExpand: true, pulseState: "sleeping", pulseText: "" });
    updateStageBadges();
    save();
  }

  function resetInactivityTimer() {
    clearTimeout(inactivityTimer);
    clearTimeout(localYawnTimer);
    localYawnTimer = null;

    // Any mouse/touch/key interaction wakes up to 'idle' and resets the timer
    if (isAutoSleeping || pet.sleeping) {
      isAutoSleeping = false;
      pet.sleeping = false;
      isLocalYawning = false;
      setBase(agentWorking ? "working" : "idle", { interrupt: true });
      show("idle");
      say(line("wake"), { suppressAutoExpand: true, pulseState: "idle", pulseText: "" });
      save();
    } else if (isLocalYawning || current === "yawn") {
      isLocalYawning = false;
      setBase(agentWorking ? "working" : "idle", { interrupt: true });
      show(base);
    }

    scheduleInactivityTimer();
  }

  function handleInactivityTimeout() {
    // Si hay telemetría nativa reciente de Windows, suspender fallback local para evitar falsos AFK
    if (pet.winEventsEnabled && lastNativeIdleAt > 0 && (Date.now() - lastNativeIdleAt) < NATIVE_IDLE_FRESH_MS) {
      scheduleInactivityTimer();
      return;
    }
    if (activeMedia && activeMedia.playing) {
      scheduleInactivityTimer();
      return;
    }
    if (agentWorking || pendingConfirmId) {
      scheduleInactivityTimer();
      return;
    }

    if (!pet.sleeping && !isLocalYawning) {
      isLocalYawning = true;
      clearTimeout(transientTimer);
      transientTimer = null;
      show("yawn");
      say(line("yawn"), { suppressAutoExpand: true, pulseState: "yawn", pulseText: "Bostezando… 🥱" });
      localYawnTimer = setTimeout(() => {
        localYawnTimer = null;
        isLocalYawning = false;
        if (pet.winEventsEnabled && lastNativeIdleAt > 0 && (Date.now() - lastNativeIdleAt) < NATIVE_IDLE_FRESH_MS) {
          show(base);
          scheduleInactivityTimer();
          return;
        }
        if ((activeMedia && activeMedia.playing) || agentWorking || pendingConfirmId) {
          show(base);
          scheduleInactivityTimer();
          return;
        }
        enterAutoSleep();
      }, YAWN_DURATION_MS);
    }
  }

  let lastUserActivityTime = 0;
  let ambientStandbyTimer = null;
  let ambientProactiveStep = 0;
  function registerUserActivity() {
    const now = performance.now();
    if (now - lastUserActivityTime < 150) return;
    lastUserActivityTime = now;
    resetInactivityTimer();
  }

  function setupLivingAvatarInteractions() {
    const activityEvents = ["pointerdown", "keydown", "wheel", "touchstart"];
    activityEvents.forEach((evt) => {
      window.addEventListener(evt, registerUserActivity, { passive: true, capture: true });
    });
    window.addEventListener("pointermove", (e) => {
      if (e.movementX !== 0 || e.movementY !== 0) {
        registerUserActivity();
      }
    }, { passive: true, capture: true });

    clearInterval(ambientStandbyTimer);
    ambientStandbyTimer = setInterval(() => {
      const inputFocused =
        document.activeElement === els.chatInput ||
        document.activeElement === els.promptInput ||
        Boolean(els.chatInput && els.chatInput.value.trim());
      if (
        pet.sleeping ||
        isAutoSleeping ||
        agentWorking ||
        pendingConfirmId ||
        transientTimer ||
        transientEventAction ||
        inputFocused ||
        (current !== "idle" && current !== "standby")
      ) {
        return;
      }

      ambientProactiveStep = (ambientProactiveStep + 1) % 8;
      if (ambientProactiveStep % 2 === 1) {
        show(current === "idle" ? "standby" : "idle");
      } else {
        const gestures = ["chill", "love", "curious", "shy"];
        const gesture = gestures[Math.floor(ambientProactiveStep / 2) % gestures.length];
        const gestureDuration = gesture === "love" || gesture === "chill" ? 4400 : 3800;
        play(gesture, null, { duration: gestureDuration, keepCurrentBrief: true });
        if (!notchExpanded && activeBrief === "avatar") {
          triggerIslandSubtlePulse(gesture);
        }
      }
    }, 18_000);

    resetInactivityTimer();
  }

  function triggerSquashAndStretch() {
    const target = els.pet || els.body;
    if (!target) return;
    try {
      target.animate([
        { transform: "scale(1, 1) translateY(0)" },
        { transform: "scale(1.24, 0.76) translateY(8px)" },
        { transform: "scale(0.82, 1.22) translateY(-12px)" },
        { transform: "scale(1.10, 0.92) translateY(3px)" },
        { transform: "scale(0.96, 1.04) translateY(-2px)" },
        { transform: "scale(1, 1) translateY(0)" }
      ], {
        duration: 750,
        easing: "cubic-bezier(0.28, 1.6, 0.45, 1)",
        fill: "none"
      });
    } catch (_) {}
  }

  // ------------------------------------------------------------------ partículas y bocadillo

  function spawnParticles(kind = "✨", count = 4) {
    if (!els.particles || !kind) return;
    const total = Math.max(1, Math.min(12, Number(count) || 1));
    const zGlyphs = ["z", "z", "Z"];
    for (let i = 0; i < total; i++) {
      const el = document.createElement("span");
      const seq = particleSeq++;
      el.className = kind === "z" ? "particle particle--z" : "particle";
      if (kind === "z") {
        el.textContent = zGlyphs[seq % zGlyphs.length];
        el.dataset.zTier = String((seq % 3) + 1);
      } else {
        el.textContent = kind === "food" ? pick(skin().food) : kind;
      }
      el.style.insetInlineStart = kind === "z" ? `${48 + Math.random() * 24}%` : `${20 + Math.random() * 60}%`;
      const dx = kind === "z" ? Math.round(12 + Math.random() * 22) : Math.round((Math.random() - 0.5) * 56);
      el.style.setProperty("--dx", `${dx}px`);
      const ttlMs = kind === "z" ? 3400 : 1950;
      const cleanup = () => el.remove();
      el.addEventListener("animationend", cleanup, { once: true });
      setTimeout(cleanup, ttlMs);
      els.particles.append(el);
    }
  }

  function startParticles(kind, every = 450) {
    clearInterval(particleTimer);
    particleTimer = null;
    if (!kind) return;
    spawnParticles(kind, 1);
    particleTimer = setInterval(() => spawnParticles(kind, 1), every);
  }

  function spawnMiniParticles(kind, count = 1) {
    const container = els.miniParticles || $("miniParticles");
    if (!container || !kind) return;
    const total = Math.max(1, Math.min(6, Number(count) || 1));
    const zGlyphs = ["z", "z", "Z"];
    const heartGlyphs = ["💖", "💕", "💗"];

    for (let i = 0; i < total; i++) {
      while (container.childElementCount >= 8) {
        container.firstElementChild?.remove();
      }
      const el = document.createElement("span");
      const idx = miniParticleSeq++;
      if (kind === "z") {
        el.className = "mini-particle mini-particle--z";
        el.textContent = zGlyphs[idx % zGlyphs.length];
        el.dataset.zTier = String((idx % 3) + 1);
      } else if (kind === "heart") {
        el.className = "mini-particle mini-particle--heart";
        el.textContent = heartGlyphs[idx % heartGlyphs.length];
      } else {
        el.className = "mini-particle mini-particle--fx";
        el.textContent = kind === "food" ? pick(skin().food) : kind;
      }
      const offsetX = Math.round(Math.random() * 14);
      const driftX = kind === "z"
        ? 8 + Math.round(Math.random() * 10)
        : -3 + Math.round(Math.random() * 13);
      el.style.setProperty("--mini-x", `${50 + offsetX}%`);
      el.style.setProperty("--mini-dx", `${driftX}px`);
      el.style.setProperty("--dx", `${driftX}px`);
      el.style.animationDelay = `${i * (kind === "z" ? 160 : 110)}ms`;
      const ttlMs = kind === "z" ? 3300 + i * 160 : 1950 + i * 110;
      const cleanup = () => el.remove();
      el.addEventListener("animationend", cleanup, { once: true });
      setTimeout(cleanup, ttlMs);
      container.append(el);
    }
  }

  function startMiniParticles(kind, every = 1100) {
    clearInterval(miniParticleTimer);
    miniParticleTimer = null;
    if (!kind) {
      return;
    }
    spawnMiniParticles(kind, 1);
    miniParticleTimer = setInterval(() => {
      spawnMiniParticles(kind, 1);
    }, every || 1100);
  }

  function syncNotifBrandColorOnStage() {
    if (!els.stage) return;
    if (notificationInbox.length > 0) {
      const topSpec = getNotificationBrandSpec(notificationInbox[0].app, notificationInbox[0].title);
      els.stage.style.setProperty("--notif-brand-color", topSpec.color);
    } else {
      els.stage.style.removeProperty("--notif-brand-color");
    }
  }

  function clearIslandSubtlePulse({ sync = true } = {}) {
    clearTimeout(islandPulseTimer);
    islandPulseTimer = null;
    islandPulsePreviewText = null;
    if (els.stage) {
      els.stage.classList.remove("is-island-pulsing");
      delete els.stage.dataset.islandPulse;
      syncNotifBrandColorOnStage();
    }
    if (sync) {
      syncIslandIllumination({ animate: false });
    }
  }

  function clearIslandMediaGlow() {
    clearTimeout(mediaGlowTimer);
    mediaGlowTimer = null;
    if (els.stage) {
      els.stage.classList.remove("is-media-glow");
      if (els.stage.dataset.islandPulse === "media") {
        delete els.stage.dataset.islandPulse;
      }
    }
  }

  function triggerIslandMediaGlow(previewText = "") {
    if (!els.stage) return;
    clearTimeout(mediaGlowTimer);
    if (!notchExpanded) {
      els.stage.classList.remove("is-media-glow");
      void els.stage.offsetWidth;
      els.stage.classList.add("is-media-glow");
      els.stage.dataset.islandPulse = "media";
    }
    if (previewText && activeBrief === "media" && els.briefMediaTitle) {
      checkAndApplyMarquee(els.briefMediaTitle, { marquee360: true, text: previewText });
    }
    mediaGlowTimer = setTimeout(() => {
      mediaGlowTimer = null;
      if (els.stage) {
        els.stage.classList.remove("is-media-glow");
        if (els.stage.dataset.islandPulse === "media") {
          delete els.stage.dataset.islandPulse;
        }
      }
    }, 3600);
  }

  function triggerIslandSubtlePulse(state = current, previewText = "", { pulseKey = null, brandColor = null, brandColor2 = null } = {}) {
    if (notchExpanded || !els.stage) return;
    clearTimeout(islandPulseTimer);
    const resolvedState = validState(state) || current || "idle";
    const pulseDataset = pulseKey || resolvedState;
    const fx = FX[resolvedState] || FX.idle;

    els.stage.classList.remove("is-island-pulsing");
    void els.stage.offsetWidth;
    if (brandColor) {
      els.stage.style.setProperty("--notif-brand-color", brandColor);
      if (pulseKey !== "notif") {
        els.stage.style.setProperty("--island-illum-1", brandColor);
        els.stage.style.setProperty("--island-illum-2", brandColor2 || brandColor);
      }
    } else {
      syncNotifBrandColorOnStage();
    }
    els.stage.dataset.islandPulse = pulseDataset;
    els.stage.classList.add("is-island-pulsing");

    const miniKind =
      fx.miniParticle ||
      (fx.particle && fx.particle !== "food" ? fx.particle : (previewText ? "✨" : null));
    if (miniKind) {
      spawnMiniParticles(miniKind, resolvedState === "love" || resolvedState === "celebrate" ? 3 : 2);
    }

    const cleanPreview = String(previewText || "").replace(/\s+/g, " ").trim();
    if (cleanPreview && activeBrief === "avatar" && els.stateLabel) {
      const clipped = cleanPreview.length > 48 ? `${cleanPreview.slice(0, 47)}…` : cleanPreview;
      islandPulsePreviewText = clipped;
      els.stateLabel.textContent = clipped;
      els.stateLabel.setAttribute("data-raw-text", clipped);
      requestAnimationFrame(() => {
        if (els.stateLabel && !notchExpanded && islandPulsePreviewText === clipped) {
          checkAndApplyMarquee(els.stateLabel, { text: clipped });
        }
      });
    } else {
      islandPulsePreviewText = null;
    }

    islandPulseTimer = setTimeout(() => {
      islandPulseTimer = null;
      islandPulsePreviewText = null;
      if (els.stage) {
        els.stage.classList.remove("is-island-pulsing");
        if (!(els.stage.classList.contains("is-media-glow") && els.stage.dataset.islandPulse === "media")) {
          delete els.stage.dataset.islandPulse;
        }
        syncNotifBrandColorOnStage();
      }
      updateStageBadges();
      syncIslandIllumination({ animate: false });
    }, 2600);
  }

  let pendingBubbleDock = null;
  let bubbleDockAnimTimer = null;
  let dockAnimResetTimer = null;

  function updateAgentDock(
    text,
    { tone = "reply", badge = "💬 Respuesta", animate = "update", speakLabel = null } = {}
  ) {
    if (!els.agentReplyDock || !els.agentDockText) return;
    const cleanText = String(text ?? "").trim();
    if (!cleanText) return;

    dockUpdateSeq += 1;
    hasDockMessage = true;
    const sk = skin();
    const speakerName = speakLabel || getCleanAvatarName(sk);
    if (els.agentDockSpeaker) els.agentDockSpeaker.textContent = speakerName;
    if (els.agentDockBadge) els.agentDockBadge.textContent = badge;
    if (els.agentDockMeta) {
      els.agentDockMeta.textContent = new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
    }
    els.agentReplyDock.dataset.tone = tone;
    els.agentDockText.textContent = cleanText;
    if (els.agentDockBody) {
      els.agentDockBody.scrollTop = 0;
    }

    if (animate !== "none") {
      clearTimeout(dockAnimResetTimer);
      els.agentReplyDock.classList.remove("is-catching", "is-updating");
      void els.agentReplyDock.offsetWidth;
      const cls = animate === "catch" ? "is-catching" : "is-updating";
      els.agentReplyDock.classList.add(cls);
      dockAnimResetTimer = setTimeout(() => {
        els.agentReplyDock?.classList.remove("is-catching", "is-updating");
      }, 420);
    }
  }

  function ensureBubbleAlwaysHidden() {
    if (els.bubble) {
      els.bubble.classList.remove("is-docking");
      if (!els.bubble.hidden) {
        hideElement(els.bubble);
      }
      els.bubble.hidden = true;
    }
  }

  async function flushBubbleToDock() {
    const queued = pendingBubbleDock;
    pendingBubbleDock = null;
    clearTimeout(bubbleDockAnimTimer);
    if (els.bubble) {
      els.bubble.classList.remove("is-docking");
      if (!els.bubble.hidden) {
        await hideElement(els.bubble);
      }
      els.bubble.hidden = true;
    }
    if (!pendingConfirmId) {
      if (els.confirmBar) els.confirmBar.hidden = true;
      if (els.bubbleTag) els.bubbleTag.hidden = true;
      if (els.agentReplyDock) delete els.agentReplyDock.dataset.confirmPending;
    }
    if (queued?.text) {
      updateAgentDock(queued.text, {
        tone: queued.tone || "idle",
        badge: queued.badge || "✨ Anclado",
        animate: "catch",
      });
    }
    requestExpandedHeightUpdate();
  }

  function flushPendingDockQueue() {
    if (!pendingDockQueue.length) return false;
    const next = pendingDockQueue[pendingDockQueue.length - 1];
    pendingDockQueue = [];
    if (!next?.text) return false;
    updateAgentDock(next.text, {
      tone: next.tone || "idle",
      badge: next.badge || "✨ Pendiente",
      animate: "update",
    });
    requestExpandedHeightUpdate();
    return true;
  }

  function say(text, options = {}) {
    if (!text) return;
    const opts = typeof options === "object" && options !== null ? options : {};
    const ms = typeof options === "number" ? options : opts.duration;
    const confirmId = opts.confirmId || null;
    const forceExpand = Boolean(opts.forceExpand);
    const suppressAutoExpand = Boolean(opts.suppressAutoExpand);
    const skipPulse = Boolean(opts.skipPulse);
    const dockTone =
      opts.dockTone || (confirmId ? "reminder" : (opts.directToDock || opts.fromChat ? "reply" : "idle"));
    const dockBadge =
      opts.dockBadge || (confirmId ? "🔐 Autorización" : (opts.directToDock || opts.fromChat ? "💬 Respuesta" : "✨ Anclado"));

    if (!confirmId && pendingConfirmId) {
      if (pendingDockQueue.length >= 10) {
        pendingDockQueue.shift();
      }
      pendingDockQueue.push({ text: String(text), tone: dockTone, badge: dockBadge });
      if (!notchExpanded && !skipPulse) {
        const pulsePreview = opts.pulseText !== undefined ? opts.pulseText : String(text);
        triggerIslandSubtlePulse(opts.pulseState || current || "idle", pulsePreview, {
          brandColor: opts.brandColor || null,
          brandColor2: opts.brandColor2 || null,
        });
      }
      return;
    }

    clearTimeout(bubbleTimer);
    clearInterval(typeTimer);
    clearTimeout(bubbleDockAnimTimer);
    pendingBubbleDock = null;
    ensureBubbleAlwaysHidden();

    const charsLen = Array.from(String(text)).length;

    if (confirmId) {
      pendingConfirmId = confirmId;
      if (els.bubbleTag) els.bubbleTag.hidden = false;
      if (els.confirmBar) els.confirmBar.hidden = false;
      if (els.agentReplyDock) els.agentReplyDock.dataset.confirmPending = "true";
      updateAgentDock(text, { tone: dockTone, badge: dockBadge, animate: "catch" });

      const ttl = ms || 120_000;
      bubbleTimer = setTimeout(() => {
        if (pendingConfirmId === confirmId) {
          pendingConfirmId = null;
          if (els.confirmBar) els.confirmBar.hidden = true;
          if (els.bubbleTag) els.bubbleTag.hidden = true;
          if (els.agentReplyDock) delete els.agentReplyDock.dataset.confirmPending;
          if (!flushPendingDockQueue()) {
            updateAgentDock("Tiempo de espera de autorización agotado.", {
              tone: "idle",
              badge: "⏱️ Expirado",
              animate: "update",
            });
            requestExpandedHeightUpdate();
          }
        }
      }, ttl);

      if (!notchExpanded) {
        if (pet.autoExpandEvents && !suppressAutoExpand) {
          if (!wasCollapsedBeforeMomentary) {
            expandNotchTemporarily(ttl + 1000);
          }
        } else if (!skipPulse) {
          if (activeBrief !== "avatar" && userPinnedBrief !== "media" && userPinnedBrief !== "notif") {
            setActiveBrief("avatar", { syncView: false });
          }
          triggerIslandSubtlePulse(opts.pulseState || "surprise", opts.pulseText ?? `🔐 ${text}`);
        }
      } else {
        requestExpandedHeightUpdate();
      }
      return;
    }

    if (els.confirmBar) els.confirmBar.hidden = true;
    if (els.bubbleTag) els.bubbleTag.hidden = true;
    if (els.agentReplyDock) delete els.agentReplyDock.dataset.confirmPending;
    updateAgentDock(text, { tone: dockTone, badge: dockBadge, animate: "update" });

    const ttl = ms || Math.min(8500, 2600 + charsLen * 45);
    if (!notchExpanded) {
      if (pet.autoExpandEvents && !suppressAutoExpand && (!focusActive || forceExpand)) {
        if (!wasCollapsedBeforeMomentary) {
          expandNotchTemporarily(ttl + 900);
        }
      } else if (!skipPulse) {
        const pulsePreview = opts.pulseText !== undefined ? opts.pulseText : String(text);
        triggerIslandSubtlePulse(opts.pulseState || current || "idle", pulsePreview, {
          brandColor: opts.brandColor || null,
          brandColor2: opts.brandColor2 || null,
        });
      }
    } else {
      requestExpandedHeightUpdate();
    }
  }

  function resolveConfirmation(approved) {
    const id = pendingConfirmId || "manual";
    const hadQueued = pendingDockQueue.length > 0;
    clearTimeout(bubbleTimer);
    pendingConfirmId = null;
    pendingBubbleDock = null;
    if (els.confirmBar) els.confirmBar.hidden = true;
    if (els.bubbleTag) els.bubbleTag.hidden = true;
    if (els.agentReplyDock) delete els.agentReplyDock.dataset.confirmPending;
    ensureBubbleAlwaysHidden();

    core.send({ type: "user.confirm", data: { id, approved } });
    logActivity("user.confirm", `${id} → ${approved ? "permitido" : "cancelado"}`);

    if (approved) {
      play("celebrate", "Autorizado. Ejecutando operación ✨", {
        directToDock: true,
        dockTone: "reply",
        dockBadge: "✅ Autorizado",
      });
    } else {
      play("idle", "Operación cancelada.", {
        directToDock: true,
        dockTone: "idle",
        dockBadge: "✕ Cancelado",
      });
    }

    if (hadQueued) {
      const seqAfterResolve = dockUpdateSeq;
      setTimeout(() => {
        if (!pendingConfirmId && dockUpdateSeq === seqAfterResolve) {
          flushPendingDockQueue();
        }
      }, 1600);
    }
  }

  els.confirmApprove?.addEventListener("click", (event) => {
    event?.stopPropagation?.();
    resolveConfirmation(true);
  });
  els.confirmReject?.addEventListener("click", (event) => {
    event?.stopPropagation?.();
    resolveConfirmation(false);
  });

  els.bubble?.addEventListener("click", async () => {
    ensureBubbleAlwaysHidden();
    requestExpandedHeightUpdate();
  });

  // ------------------------------------------------------------------ cambio de personaje y acciones

  function onPetClick() {
    if (pet.sleeping) {
      wake();
      return;
    }
    const now = Date.now();
    if (now - lastPet < 450) return;
    lastPet = now;
    els.pet.classList.add("is-clicked");
    setTimeout(() => els.pet.classList.remove("is-clicked"), 200);
    const clickMoods = ["happy", "love", "excited", "shy", "proud", "curious", "chill"];
    const nextMood = clickMoods[petClickMoodIndex % clickMoods.length];
    petClickMoodIndex += 1;
    play(nextMood, line(nextMood));
  }

  function setSkin(id) {
    if (!CATALOG.skins[id]) return;
    pet.skin = id;
    preload(skin());
    if (els.miniThumb) els.miniThumb.src = skin().sprites.idle;
    renderPixel();
    show(current);
    updateStageBadges();
    updateAllMarquees();
    say(line("greet"));
    renderSkinCards();
    if (core.connected) {
      core.send({ type: "client.hello", data: { client: "pet", skin: pet.skin } });
    }
    save();
  }

  function toggleStyle() {
    pet.style = "anime";
    renderPixel();
    save();
  }

  function applyTheme(theme) {
    pet.theme = theme === "light" ? "light" : "dark";
    document.documentElement.dataset.theme = pet.theme;
    const isLight = pet.theme === "light";
    if (els.themeToggle) {
      els.themeToggle.classList.toggle("is-active", isLight);
      els.themeToggle.setAttribute("aria-checked", String(isLight));
      const lbl = els.themeToggle.querySelector(".win-switch__label");
      if (lbl) {
        lbl.textContent = isLight ? "☀️ Tema claro" : "🌙 Tema oscuro";
      } else {
        els.themeToggle.textContent = isLight ? "🌙 Tema oscuro" : "☀️ Tema claro";
      }
    }
  }

  function setPrivateMode(enabled, { persist = true } = {}) {
    pet.privateMode = Boolean(enabled);
    const privBtn = els.privateToggleBtn || $("privateToggleBtn");
    if (privBtn) {
      privBtn.classList.toggle("is-active", pet.privateMode);
      privBtn.setAttribute("aria-checked", String(pet.privateMode));
    }
    if (persist) {
      save(pet);
    }
  }

  function setAutoExpandMode(enabled, { persist = true } = {}) {
    pet.autoExpandEvents = Boolean(enabled);
    if (persist) {
      pet.autoExpandManual = true;
    }
    const autoBtn = els.autoExpandToggleBtn || $("autoExpandToggleBtn");
    if (autoBtn) {
      autoBtn.classList.toggle("is-active", pet.autoExpandEvents);
      autoBtn.setAttribute("aria-checked", String(pet.autoExpandEvents));
    }
    if (persist) {
      save(pet);
    }
  }

  function setWinEventsEnabled(enabled, { persist = true } = {}) {
    pet.winEventsEnabled = Boolean(enabled);
    const winBtn = els.winEventsToggleBtn || $("winEventsToggleBtn");
    if (winBtn) {
      winBtn.classList.toggle("is-active", pet.winEventsEnabled);
      winBtn.setAttribute("aria-checked", String(pet.winEventsEnabled));
    }
    if (persist) {
      save(pet);
    }
  }

  async function syncAutoStartUI(explicitState) {
    const btn = els.autoStartToggleBtn || $("autoStartToggleBtn");
    if (!btn) return;
    if (!hasNativeHost() || typeof window.mekaGetAutoStart !== "function") {
      btn.hidden = true;
      return;
    }
    btn.hidden = false;
    try {
      const enabled = typeof explicitState === "boolean"
        ? explicitState
        : Boolean(await Promise.resolve(window.mekaGetAutoStart()));
      btn.classList.toggle("is-active", enabled);
      btn.setAttribute("aria-checked", String(enabled));
    } catch (_) {
      // Silencioso si el host aún inicializa
    }
  }

  async function toggleAutoStart() {
    if (typeof window.mekaSetAutoStart !== "function") return;
    const btn = els.autoStartToggleBtn || $("autoStartToggleBtn");
    const next = !(btn && btn.getAttribute("aria-checked") === "true");
    try {
      const resulting = Boolean(await Promise.resolve(window.mekaSetAutoStart(next)));
      await syncAutoStartUI(resulting);
    } catch (_) {
      await syncAutoStartUI();
    }
  }

  function setGlassMode(mode, { persist = true } = {}) {
    const nextGlass = mode === "normal" ? "normal" : "liquid";
    pet.glass = nextGlass;
    document.documentElement.dataset.glass = nextGlass;
    if (els.stage) {
      els.stage.dataset.glass = nextGlass;
    }
    const isLiquid = nextGlass === "liquid";
    const glassBtn = els.glassToggleBtn || $("glassToggleBtn");
    if (glassBtn) {
      glassBtn.classList.toggle("is-active", isLiquid);
      glassBtn.setAttribute("aria-checked", String(isLiquid));
    }
    if (persist) {
      save(pet);
    }
  }

  function launchPopout() {
    const url = new URL(location.href);
    url.searchParams.set("desktop", "1");
    window.open(
      url.toString(),
      "MekaCompanionPopup",
      "width=300,height=380,menubar=no,toolbar=no,location=no,status=no,resizable=no"
    );
  }

  els.popoutBtn?.addEventListener("click", launchPopout);
  els.styleToggleBtn?.addEventListener("click", toggleStyle);

  els.menuBtn?.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleSettingsCard();
  });

  // ------------------------------------------------------------------ chat con el agente

  els.chatForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const text = els.chatInput.value.trim();
    if (!text) return;
    els.chatInput.value = "";
    logActivity("user.message", pet.privateMode ? `🔒 ${text}` : text);
    if (core.connected) {
      core.send({
        type: "user.message",
        data: { text, private: Boolean(pet.privateMode) },
      });
      play("thinking", null, { duration: 15_000 });
      updateAgentDock("Procesando tu mensaje…", {
        tone: "working",
        badge: pet.privateMode ? "🔒 Pensando…" : "💭 Pensando…",
        animate: "update",
      });
    } else {
      play("thinking");
      updateAgentDock("Pensando…", {
        tone: "working",
        badge: "💭 En chat",
        animate: "update",
      });
      setTimeout(() => {
        play("happy", line("chat"), {
          directToDock: true,
          dockTone: "reply",
          dockBadge: "💬 Respuesta",
        });
      }, 900);
    }
  });

  // ------------------------------------------------------------------ menú contextual rápido

  let screenshotHideTimer = null;

  function hideTemporarilyForScreenshot(seconds = 10) {
    clearTimeout(screenshotHideTimer);
    els.stage?.classList.add("is-screenshot-hidden");
    if (typeof window.mekaSetWindowVisible === "function") {
      window.mekaSetWindowVisible(false);
    }
    screenshotHideTimer = setTimeout(() => {
      restoreScreenshotHidden();
    }, seconds * 1000);
  }

  function restoreScreenshotHidden() {
    clearTimeout(screenshotHideTimer);
    els.stage?.classList.remove("is-screenshot-hidden");
    if (typeof window.mekaSetWindowVisible === "function") {
      window.mekaSetWindowVisible(true);
    }
  }

  function centerNotch() {
    if (typeof window.mekaCenterNotch === "function") {
      window.mekaCenterNotch();
    }
  }

  function toggleDodge() {
    if (typeof window.mekaToggleDodge === "function") {
      window.mekaToggleDodge();
    }
  }

  function closeMekaApplication(event) {
    event?.stopPropagation();
    if (typeof window.mekaCloseWindow === "function") {
      window.mekaCloseWindow();
      return;
    }
    window.close();
  }

  function menuItems() {
    const items = [];
    if (notificationInbox.length > 0) {
      const topNotif = notificationInbox[0];
      const emoji = getNotificationEmoji(topNotif.app, topNotif.title);
      items.push(
        [`${emoji} Notificación: ${topNotif.app || "App"} (Abrir)`, () => openNotification(topNotif.id)],
        [`✕ Marcar como vista (${topNotif.app || "App"})`, () => dismissNotification(topNotif.id)]
      );
      if (notificationInbox.length > 1) {
        items.push([`🧹 Limpiar todas (${notificationInbox.length})`, () => clearAllNotifications()]);
      }
      items.push("sep");
    }
    items.push(
      ["⚙️ Ajustes y modos", () => setSettingsCardOpen(true)],
      [
        focusActive ? "🎯 Modo concentración: ON" : "🎯 Modo concentración: OFF",
        () => (focusActive ? stopFocus() : startFocus()),
      ],
      [
        pet.glass === "liquid" ? "💧 Estilo: Liquid Glass" : "🌑 Estilo: Normal Oscuro",
        () => setGlassMode(pet.glass === "liquid" ? "normal" : "liquid"),
      ],
      [
        pet.privateMode ? "🔒 Modo privado: ON" : "🔓 Modo privado: OFF",
        () => setPrivateMode(!pet.privateMode),
      ],
      ["✨ ¿Qué tengo pendiente?", () => triggerProactiveCheck()],
      [pet.sleeping ? "☀️ Activar" : "😴 Modo reposo", () => (pet.sleeping ? wake() : sleep())],
      "sep",
      ["📸 Ocultar 10s (para captura)", () => hideTemporarilyForScreenshot(10)],
      ["↔ Esquivar centro / Volver", toggleDodge],
      ["🎯 Centrar en pantalla", centerNotch],
    );
    if (!IS_DESKTOP) items.push(["🗗 Ventana flotante", launchPopout]);
    if (hasNativeHost()) {
      items.push("sep", ["✖ Cerrar aplicación", () => window.mekaCloseWindow?.()]);
    }
    return items;
  }

  function openMenu(clientX, clientY) {
    els.menu.replaceChildren();
    for (const item of menuItems()) {
      const li = document.createElement("li");
      if (item === "sep") {
        li.className = "sep";
      } else if (typeof item === "string") {
        li.className = "title";
        li.textContent = item;
      } else {
        const [label, action] = item;
        const button = document.createElement("button");
        button.type = "button";
        button.setAttribute("role", "menuitem");
        button.textContent = label;
        button.addEventListener("click", () => {
          closeMenu();
          action();
        });
        li.append(button);
      }
      els.menu.append(li);
    }
    showElement(els.menu);
    const stage = els.stage.getBoundingClientRect();
    const left = Math.min(Math.max(clientX - stage.left, 8), stage.width - els.menu.offsetWidth - 8);
    const top = Math.min(Math.max(clientY - stage.top, 8), stage.height - els.menu.offsetHeight - 8);
    els.menu.style.insetInlineStart = `${Math.max(8, left)}px`;
    els.menu.style.insetBlockStart = `${Math.max(8, top)}px`;
    els.menu.querySelector("button")?.focus();
    if (typeof window.mekaSetInteractiveOverlay === "function") {
      window.mekaSetInteractiveOverlay(true);
    }
  }

  function closeMenu() {
    hideElement(els.menu);
    if (typeof window.mekaSetInteractiveOverlay === "function") {
      window.mekaSetInteractiveOverlay(false);
    }
  }

  document.addEventListener("pointerdown", (event) => {
    if (!els.menu.hidden && !els.menu.contains(event.target)) closeMenu();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeMenu();
      if (pendingConfirmId) resolveConfirmation(false);
    }
  });

  // ------------------------------------------------------------------ puntero: interactuar, arrastrar, menú

  const offset = { x: 0, y: 0 };
  let press = null;

  function startWindowDrag() {
    if (typeof window.mekaStartDrag === "function") {
      window.mekaStartDrag();
    }
  }

  let stageTopPress = null;
  let stageWasDragged = false;
  const stageTop = $("stageTop") || document.querySelector(".stage__top");
  stageTop?.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 || event.target.closest("button") || event.target.closest("input")) return;
    stageTopPress = { x: event.clientX, y: event.clientY, moved: false };
  });

  stageTop?.addEventListener("pointermove", (event) => {
    if (!stageTopPress) return;
    const dx = event.clientX - stageTopPress.x;
    const dy = event.clientY - stageTopPress.y;
    if (!stageTopPress.moved && Math.hypot(dx, dy) >= 6) {
      stageTopPress.moved = true;
      stageWasDragged = true;
      if (hasNativeHost()) {
        startWindowDrag();
      }
    }
  });

  stageTop?.addEventListener("pointerup", () => {
    stageTopPress = null;
  });
  stageTop?.addEventListener("pointercancel", () => {
    stageTopPress = null;
  });
  stageTop?.addEventListener("dblclick", (event) => {
    if (event.target.closest("button") || event.target.closest("input")) return;
    centerNotch();
  });

  els.pet.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    press = { x: event.clientX, y: event.clientY, ox: offset.x, oy: offset.y, moved: false };
    press.long = setTimeout(() => {
      if (press && !press.moved) {
        openMenu(press.x, press.y);
        press = null;
      }
    }, 600);
    els.pet.setPointerCapture(event.pointerId);
  });

  els.pet.addEventListener("pointermove", (event) => {
    if (!press) return;
    const dx = event.clientX - press.x;
    const dy = event.clientY - press.y;
    if (!press.moved) {
      if (Math.hypot(dx, dy) < 6) return;
      press.moved = true;
      clearTimeout(press.long);
      if (hasNativeHost()) {
        try {
          els.pet.releasePointerCapture(event.pointerId);
        } catch (_) {}
        press = null;
        startWindowDrag();
        return;
      }
      els.pet.classList.add("is-dragging");
    }
    offset.x = Math.max(-80, Math.min(80, press.ox + dx));
    offset.y = Math.max(-90, Math.min(30, press.oy + dy));
    els.pet.style.translate = `${offset.x}px ${offset.y}px`;
  });

  function endPress(event, cancelled) {
    if (!press) return;
    clearTimeout(press.long);
    const wasDrag = press.moved;
    press = null;
    els.pet.classList.remove("is-dragging");
    if (!wasDrag && !cancelled) onPetClick();
  }

  els.pet.addEventListener("pointerup", (event) => endPress(event, false));
  els.pet.addEventListener("pointercancel", (event) => endPress(event, true));
  els.pet.addEventListener("contextmenu", (event) => {
    event.preventDefault();
    openMenu(event.clientX, event.clientY);
  });
  els.pet.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onPetClick();
    } else if (event.key === "ContextMenu" || (event.shiftKey && event.key === "F10")) {
      event.preventDefault();
      const rect = els.pet.getBoundingClientRect();
      openMenu(rect.left + rect.width / 2, rect.top + 20);
    }
  });
  els.pet.addEventListener("dblclick", (event) => {
    event.stopPropagation();
    if (pet.sleeping || isAutoSleeping) {
      wake({ quiet: true });
    }
    petDoubleClickToggle = !petDoubleClickToggle;
    const specialMood = petDoubleClickToggle ? "love" : "excited";
    const burstParticle = specialMood === "love" ? "💖" : "🌟";
    triggerSquashAndStretch();
    play(specialMood, line(specialMood), { suppressAutoExpand: true });
    spawnParticles(burstParticle, 8);
    spawnMiniParticles(specialMood === "love" ? "heart" : "🌟", 4);
  });

  // ------------------------------------------------------------------ Samsung Brief & One UI 9 Logic

  const BRIEFS = ["avatar", "media", "notif"];
  let activeBrief = "avatar";
  let briefPreviewTimer = null;
  let userPinnedBrief = null;
  let userPinnedBriefTimer = null;
  const notificationInbox = [];
  const seenNotificationIds = new Set();
  let initialNotificationsLoaded = false;
  let systemSyncTimer = null;

  const STATE_ILLUM_PALETTES = {
    idle: ["#38bdf8", "#0284c7"],
    standby: ["#38bdf8", "#0284c7"],
    working: ["#0a84ff", "#38bdf8"],
    thinking: ["#38bdf8", "#64d2ff"],
    curious: ["#38bdf8", "#0ea5e9"],
    sleeping: ["#8b5cf6", "#6366f1"],
    yawn: ["#a78bfa", "#8b5cf6"],
    love: ["#fb7185", "#f43f5e"],
    happy: ["#ff375f", "#fb7185"],
    greet: ["#f472b6", "#ec4899"],
    shy: ["#f9a8d4", "#f472b6"],
    chill: ["#2dd4bf", "#06b6d4"],
    surprise: ["#fbbf24", "#f59e0b"],
    excited: ["#f59e0b", "#fbbf24"],
    celebrate: ["#ffd60a", "#f59e0b"],
    proud: ["#eab308", "#facc15"],
    dance: ["#38bdf8", "#ec4899"],
    eating: ["#ff9f0a", "#f97316"],
    charging: ["#4ade80", "#facc15"],
    gaming: ["#818cf8", "#c084fc"],
    focus: ["#38bdf8", "#0ea5e9"],
    sad: ["#64748b", "#475569"],
    sigh: ["#94a3b8", "#64748b"],
    dizzy: ["#f59e0b", "#94a3b8"],
    error: ["#ff453a", "#ef4444"],
  };
  let activeMediaAccents = ["#38bdf8", "#0ea5e9"];
  let lastIllumSignature = "";
  let illumTransitionTimer = null;

  function pinUserBrief(name) {
    clearTimeout(userPinnedBriefTimer);
    userPinnedBriefTimer = null;
    userPinnedBrief = name;
    if (name === "avatar") {
      userPinnedBriefTimer = setTimeout(() => {
        if (userPinnedBrief === "avatar") {
          userPinnedBrief = null;
        }
        userPinnedBriefTimer = null;
      }, 30_000);
    }
  }

  // Marquee horizontal text scrolling (One UI 9) & 360° continuous carousel
  function checkAndApplyMarquee(element, options = {}) {
    if (!element) return;
    const wrapper = element.closest ? element.closest(".marquee-wrapper") : null;

    const is360 = Boolean(
      options.marquee360 ||
      element.id === "briefMediaTitle" ||
      element.classList.contains("marquee-360") ||
      (wrapper && wrapper.classList.contains("marquee-360")) ||
      element.dataset.marquee360 === "true"
    );

    // Retrieve or set original text (clean of duplicate spans)
    let rawText = options.text;
    if (rawText !== undefined) {
      element.setAttribute("data-raw-text", rawText);
    } else {
      const firstSpan = element.querySelector(".marquee-item--primary");
      if (firstSpan) {
        rawText = element.getAttribute("data-raw-text") || firstSpan.textContent.trim();
      } else {
        rawText = element.textContent.trim() || element.getAttribute("data-raw-text") || "";
        element.setAttribute("data-raw-text", rawText);
      }
    }

    // Temporarily remove classes and custom properties to measure accurately
    element.classList.remove("is-marquee", "is-marquee-360");
    if (wrapper) wrapper.classList.remove("is-marquee", "is-marquee-360");
    element.style.removeProperty("--marquee-scroll-x");
    element.style.removeProperty("--marquee-distance");
    element.style.removeProperty("--marquee-duration");

    element.textContent = rawText;

    const scrollWidth = element.scrollWidth;
    const clientWidth = wrapper ? wrapper.clientWidth : element.clientWidth;

    if (scrollWidth > clientWidth && clientWidth > 0) {
      if (is360) {
        // Build dual-span loop content if text overflows so it rolls seamlessly in an infinite 360° carousel
        const separator = "\u00A0\u00A0\u00A0\u00A0·\u00A0\u00A0\u00A0\u00A0";
        element.innerHTML = "";

        const span1 = document.createElement("span");
        span1.className = "marquee-item marquee-item--primary";
        span1.textContent = rawText + separator;

        const span2 = document.createElement("span");
        span2.className = "marquee-item marquee-item--duplicate";
        span2.setAttribute("aria-hidden", "true");
        span2.textContent = rawText + separator;

        element.appendChild(span1);
        element.appendChild(span2);

        const spanWidth = span1.offsetWidth || scrollWidth;
        const duration = Math.max(5.0, Math.min(25.0, (spanWidth / 25) + 3.0));

        element.style.setProperty("--marquee-scroll-x", `-${spanWidth}px`);
        element.style.setProperty("--marquee-distance", `-${spanWidth}px`);
        element.style.setProperty("--marquee-duration", `${duration.toFixed(1)}s`);
        element.classList.add("is-marquee", "is-marquee-360");
        if (wrapper) wrapper.classList.add("is-marquee", "is-marquee-360");
      } else {
        const distance = scrollWidth - clientWidth + 8;
        const duration = Math.max(4.0, Math.min(16.0, (distance / 22) + 3.0));
        element.style.setProperty("--marquee-scroll-x", `-${distance}px`);
        element.style.setProperty("--marquee-duration", `${duration.toFixed(1)}s`);
        element.classList.add("is-marquee");
        if (wrapper) wrapper.classList.add("is-marquee");
      }
    } else {
      element.textContent = rawText;
    }
  }

  function updateAllMarquees() {
    requestAnimationFrame(() => {
      const sk = skin();
      const fx = FX[current] || FX.idle;
      const cleanName = getCleanAvatarName(sk);
      const displayName = transientEventAction
        ? `${cleanName} · ${transientEventAction}`
        : cleanName;
      if (els.skinNameLabel) {
        checkAndApplyMarquee(els.skinNameLabel, { text: displayName });
      }
      const moodLabel = computeMoodLabel();
      if (els.stateLabel) {
        checkAndApplyMarquee(els.stateLabel, { text: moodLabel });
      }
      if (els.briefMediaTitle) {
        const singleLine = activeMedia && (activeMedia.title || activeMedia.artist)
          ? (activeMedia.artist ? `${activeMedia.title} · ${activeMedia.artist}` : activeMedia.title)
          : "Sin reproducción";
        checkAndApplyMarquee(els.briefMediaTitle, { marquee360: true, text: singleLine });
      }
      if (els.briefNotifTitle) {
        const notifTitle = els.briefNotifTitle.getAttribute("data-raw-text") || els.briefNotifTitle.textContent;
        checkAndApplyMarquee(els.briefNotifTitle, { marquee360: true, text: notifTitle });
      }
      if (els.briefNotifSubtitle) {
        els.briefNotifSubtitle.hidden = true;
      }
      if (els.mediaTitle) checkAndApplyMarquee(els.mediaTitle);
      if (els.mediaArtist) checkAndApplyMarquee(els.mediaArtist);
    });
  }

  const BRAND_ICONS = {
    whatsapp: {
      brand: "whatsapp",
      color: "#25d366",
      emoji: "💬",
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20.5 11.5a8.5 8.5 0 0 1-12.56 7.46L4 20l1.08-3.82A8.5 8.5 0 1 1 20.5 11.5z"/><path d="M9.4 9.1c.25-.45.55-.46.82-.45.22.01.44.02.63.48.24.58.78 1.98.85 2.12.07.14.12.31.02.5-.1.19-.15.3-.3.47-.14.17-.3.37-.43.5-.14.14-.3.3-.13.59.17.29.74 1.22 1.6 1.98 1.1.98 2.02 1.29 2.31 1.43.29.14.46.12.63-.07.17-.19.72-.84.91-1.13.19-.29.38-.24.64-.14.26.1 1.66.78 1.94.92.28.14.47.21.54.33.07.12.07.69-.17 1.36-.24.67-1.39 1.28-1.92 1.35-.49.07-1.12.1-1.8-.12-.42-.14-.96-.32-1.66-.62-2.92-1.26-4.82-4.21-4.97-4.4-.14-.2-1.18-1.57-1.18-3 0-1.43.75-2.13 1.02-2.42z" fill="currentColor" stroke="none"/></svg>',
    },
    telegram: {
      brand: "telegram",
      color: "#38bdf8",
      emoji: "💬",
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21.2 4.4 2.8 11.7l6.1 2.2 2.4 6 3.1-3.6 4.7 3.5z"/><path d="M8.9 13.9 21.2 4.4"/></svg>',
    },
    discord: {
      brand: "discord",
      color: "#818cf8",
      emoji: "🎮",
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7.5 6.5a13 13 0 0 1 9 0l2 2.8a11 11 0 0 1 1 6.7l-3 1.5-1.3-1.7a9 9 0 0 1-6.4 0L7.5 17.5l-3-1.5a11 11 0 0 1 1-6.7z"/><circle cx="9.6" cy="12" r="1.1" fill="currentColor" stroke="none"/><circle cx="14.4" cy="12" r="1.1" fill="currentColor" stroke="none"/></svg>',
    },
    slack: {
      brand: "slack",
      color: "#c084fc",
      emoji: "💼",
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="10" width="7" height="3" rx="1.5"/><rect x="14" y="11" width="7" height="3" rx="1.5"/><rect x="10" y="3" width="3" height="7" rx="1.5"/><rect x="11" y="14" width="3" height="7" rx="1.5"/></svg>',
    },
    spotify: {
      brand: "spotify",
      color: "#1ed760",
      emoji: "🎵",
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M7.8 9.6c2.9-.8 6.1-.5 8.7.7"/><path d="M8.5 12.6c2.3-.6 4.8-.4 6.9.6"/><path d="M9.3 15.5c1.7-.4 3.5-.3 5.1.4"/></svg>',
    },
    mail: {
      brand: "mail",
      color: "#fb7185",
      emoji: "📧",
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="m4 7 8 6 8-6"/></svg>',
    },
    security: {
      brand: "security",
      color: "#fbbf24",
      emoji: "🛡️",
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3 5 6v5.5c0 4.5 2.9 8.2 7 9.5 4.1-1.3 7-5 7-9.5V6z"/><path d="m9.5 12 1.8 1.8 3.4-3.6"/></svg>',
    },
    terminal: {
      brand: "terminal",
      color: "#e2e8f0",
      emoji: "⚙️",
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.95" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2.5"/><path d="m7.5 9.5 3 2.5-3 2.5"/><path d="M12.5 14.5h4"/></svg>',
    },
    calendar: {
      brand: "calendar",
      color: "#f472b6",
      emoji: "⏰",
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="13" r="7.5"/><path d="M12 9.5V13l2.4 1.6"/><path d="M9.5 3.5h5"/></svg>',
    },
    browser: {
      brand: "browser",
      color: "#60a5fa",
      emoji: "🌐",
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3.6 9h16.8"/><path d="M3.6 15h16.8"/><path d="M12 3a13 13 0 0 1 0 18 13 13 0 0 1 0-18z"/></svg>',
    },
    files: {
      brand: "files",
      color: "#a78bfa",
      emoji: "📁",
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 7a2 2 0 0 1 2-2h4.2l2 2.4H19a2 2 0 0 1 2 2V17a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>',
    },
    system: {
      brand: "system",
      color: "#38bdf8",
      emoji: "🔔",
      svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>',
    },
  };

  function getNotificationBrandSpec(app, title) {
    const raw = `${app || ""} ${title || ""}`.toLowerCase();
    if (!raw.trim()) return BRAND_ICONS.system;
    if (/whatsapp/.test(raw)) return BRAND_ICONS.whatsapp;
    if (/(?:telegram|signal|mensajer[ií]a|chat|sms|message)/.test(raw)) return BRAND_ICONS.telegram;
    if (/discord/.test(raw)) return BRAND_ICONS.discord;
    if (/(?:slack|teams)/.test(raw)) return BRAND_ICONS.slack;
    if (/(?:alerta|seguridad|firewall|defender|antivirus|security|threat|danger|warning)/.test(raw)) {
      return BRAND_ICONS.security;
    }
    if (/(?:powershell|terminal|cmd|git|code|vscode|sistema|windows update|windows|configuraci[oó]n|settings|system)/.test(raw)) {
      return BRAND_ICONS.terminal;
    }
    if (/(?:spotify|m[uú]sica|youtube music|sonido|audio|music)/.test(raw)) return BRAND_ICONS.spotify;
    if (/(?:outlook|gmail|correo|mail)/.test(raw)) return BRAND_ICONS.mail;
    if (/(?:calendario|calendar|reloj|alarma|alarm|clock|timer|temporizador)/.test(raw)) {
      return BRAND_ICONS.calendar;
    }
    if (/(?:edge|chrome|firefox|navegador|browser|safari|opera|brave)/.test(raw)) return BRAND_ICONS.browser;
    if (/(?:descargas?|download|archivos?|explorador|file)/.test(raw)) return BRAND_ICONS.files;
    return BRAND_ICONS.system;
  }

  // Dynamic notification emojis mapping
  function getNotificationEmoji(app, title) {
    const raw = `${app || ""} ${title || ""}`.toLowerCase();
    if (!raw.trim()) return "🔔";

    // 1. WhatsApp, Telegram, Signal, Mensajería -> '💬'
    if (/(?:whatsapp|telegram|signal|mensajer[ií]a|chat|sms|message)/.test(raw)) {
      return "💬";
    }
    // 2. Discord -> '🎮'
    if (/discord/.test(raw)) {
      return "🎮";
    }
    // 2b. Slack, Teams -> '💼'
    if (/(?:slack|teams)/.test(raw)) {
      return "💼";
    }
    // 3. Alertas, Seguridad, Firewall, Defender -> '🛡️' (antes de Windows genérico)
    if (/(?:alerta|seguridad|firewall|defender|antivirus|security|threat|danger|warning)/.test(raw)) {
      return "🛡️";
    }
    // 4. Sistema, Windows, Windows Update, Configuración, PowerShell -> '⚙️'
    if (/(?:sistema|windows update|windows|configuraci[oó]n|powershell|terminal|cmd|settings|system)/.test(raw)) {
      return "⚙️";
    }
    // 5. Spotify, Música, YouTube Music, Sonido -> '🎵'
    if (/(?:spotify|m[uú]sica|youtube music|sonido|audio|music)/.test(raw)) {
      return "🎵";
    }
    // 6. Outlook, Gmail, Correo, Mail -> '📧'
    if (/(?:outlook|gmail|correo|mail)/.test(raw)) {
      return "📧";
    }
    // 7. Calendario -> '📅'
    if (/(?:calendario|calendar)/.test(raw)) {
      return "📅";
    }
    // 7b. Reloj, Alarma -> '⏰'
    if (/(?:reloj|alarma|alarm|clock|timer|temporizador)/.test(raw)) {
      return "⏰";
    }
    // 8. Edge, Chrome, Firefox, Navegador -> '🌐'
    if (/(?:edge|chrome|firefox|navegador|browser|safari|opera|brave)/.test(raw)) {
      return "🌐";
    }
    // 9. Descargas, Archivo, Explorador -> '📁'
    if (/(?:descargas?|download|archivos?|explorador|file)/.test(raw)) {
      return "📁";
    }

    // 10. Fallback -> '🔔'
    return "🔔";
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatNotifTime(time) {
    if (!time) return "Ahora";
    const ts = typeof time === "number" ? (time > 1e11 ? time : time * 1000) : Date.now();
    const date = new Date(ts);
    if (isNaN(date.getTime())) return "Ahora";
    const now = Date.now();
    const diffSec = Math.floor((now - date.getTime()) / 1000);
    if (diffSec < 45) return "Ahora";
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m`;
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function syncIslandIllumination({ animate = true } = {}) {
    if (!els.stage) return;

    let c1;
    let c2;
    if (activeBrief === "media") {
      if (activeMedia && (activeMedia.title || activeMedia.playing)) {
        [c1, c2] = activeMediaAccents;
      } else {
        [c1, c2] = ["#38bdf8", "#0284c7"];
      }
    } else if (activeBrief === "notif") {
      if (notificationInbox.length > 0) {
        const spec = getNotificationBrandSpec(notificationInbox[0].app, notificationInbox[0].title);
        c1 = spec.color;
        c2 = spec.color;
        els.stage.style.setProperty("--notif-brand-color", spec.color);
      } else {
        [c1, c2] = ["#38bdf8", "#0284c7"];
        els.stage.style.setProperty("--notif-brand-color", "#38bdf8");
      }
    } else {
      [c1, c2] = STATE_ILLUM_PALETTES[current] || STATE_ILLUM_PALETTES.idle;
    }

    els.stage.setAttribute("data-active-brief", activeBrief);
    els.stage.style.setProperty("--island-illum-1", c1);
    els.stage.style.setProperty("--island-illum-2", c2);

    const signature = `${activeBrief}:${c1}:${c2}`;
    if (signature !== lastIllumSignature) {
      lastIllumSignature = signature;
      if (animate) {
        clearTimeout(illumTransitionTimer);
        els.stage.classList.remove("is-illum-transitioning");
        void els.stage.offsetWidth;
        els.stage.classList.add("is-illum-transitioning");
        illumTransitionTimer = setTimeout(() => {
          illumTransitionTimer = null;
          els.stage?.classList.remove("is-illum-transitioning");
        }, 840);
      }
    }
  }

  function setActiveBrief(name, { syncView = true, animate = true } = {}) {
    if (!BRIEFS.includes(name)) return;
    activeBrief = name;

    if (els.stage) {
      els.stage.setAttribute("data-active-brief", activeBrief);
    }
    if (els.skinBadge) {
      els.skinBadge.setAttribute("data-active-brief", activeBrief);
    }

    if (els.briefAvatar) {
      els.briefAvatar.classList.toggle("is-active", activeBrief === "avatar");
      els.briefAvatar.setAttribute("aria-hidden", String(activeBrief !== "avatar"));
    }
    if (els.briefMedia) {
      els.briefMedia.classList.toggle("is-active", activeBrief === "media");
      els.briefMedia.setAttribute("aria-hidden", String(activeBrief !== "media"));
    }
    if (els.briefNotif) {
      els.briefNotif.classList.toggle("is-active", activeBrief === "notif");
      els.briefNotif.setAttribute("aria-hidden", String(activeBrief !== "notif"));
    }

    if (els.briefDots) {
      const dots = els.briefDots.querySelectorAll("[data-brief-dot]");
      dots.forEach((dot) => {
        const isSelected = dot.dataset.briefDot === activeBrief;
        dot.classList.toggle("is-active", isSelected);
        dot.setAttribute("aria-selected", String(isSelected));
      });
    }

    // Sync expanded view with active brief solo en navegación directa del usuario
    if (syncView && notchExpanded && !skinsCardOpen && !wasCollapsedBeforeMomentary) {
      setStageView(briefToStageView(activeBrief));
    }

    syncIslandIllumination({ animate });
    updateAllMarquees();
  }

  function stepBrief(direction) {
    const curIdx = BRIEFS.indexOf(activeBrief);
    const nextIdx = (curIdx + direction + BRIEFS.length) % BRIEFS.length;
    const next = BRIEFS[nextIdx];
    pinUserBrief(next);
    setActiveBrief(next);
  }

  function previewBrief(name, durationMs = 9000) {
    clearTimeout(briefPreviewTimer);
    const prevBrief = activeBrief;
    const shouldStayOnMedia = Boolean(activeMedia && activeMedia.playing && userPinnedBrief !== "avatar");
    const returnTarget = shouldStayOnMedia
      ? "media"
      : (prevBrief === name ? "avatar" : prevBrief);
    setActiveBrief(name, { syncView: false });
    briefPreviewTimer = setTimeout(() => {
      if (activeBrief === name) {
        const stillPlaying = Boolean(activeMedia && activeMedia.playing && userPinnedBrief !== "avatar");
        const nextTarget = stillPlaying ? "media" : returnTarget;
        setActiveBrief(nextTarget, { syncView: false });
      }
    }, durationMs);
  }

  function renderNotifBrief() {
    if (!els.briefNotif) return;
    const count = notificationInbox.length;
    let singleLine;
    if (count === 0) {
      singleLine = "Notificaciones · Al día ✨";
      if (els.briefNotifTitle) {
        els.briefNotifTitle.textContent = singleLine;
        els.briefNotifTitle.setAttribute("data-raw-text", singleLine);
      }
      if (els.briefNotifSubtitle) {
        els.briefNotifSubtitle.textContent = "";
        els.briefNotifSubtitle.hidden = true;
      }
      if (els.briefNotifDot) {
        els.briefNotifDot.classList.remove("has-unread");
        els.briefNotifDot.removeAttribute("data-count");
      }
      els.briefNotif.removeAttribute("data-unread");
      els.briefNotif.removeAttribute("data-count");
      if (els.briefNotifBrand) {
        els.briefNotifBrand.innerHTML = "";
        els.briefNotifBrand.hidden = true;
        els.briefNotifBrand.removeAttribute("data-brand");
      }
      if (els.briefNotifEmoji) {
        els.briefNotifEmoji.textContent = "🔔";
        els.briefNotifEmoji.hidden = true;
      }
      if (els.briefNotifIcon) {
        els.briefNotifIcon.classList.remove("has-emoji", "has-brand");
        els.briefNotifIcon.removeAttribute("data-brand");
      }
      if (els.stage) els.stage.style.removeProperty("--notif-brand-color");
      els.briefNotif.style.removeProperty("--notif-brand-color");
    } else {
      const latest = notificationInbox[0];
      const spec = getNotificationBrandSpec(latest.app, latest.title);
      const app = latest.app || "Notificación";
      const title = latest.title || "";
      const body = latest.body || "";
      singleLine = `${app} · ${title || body || "Nueva notificación"}`;
      if (els.briefNotifTitle) {
        els.briefNotifTitle.textContent = singleLine;
        els.briefNotifTitle.setAttribute("data-raw-text", singleLine);
      }
      if (els.briefNotifSubtitle) {
        els.briefNotifSubtitle.textContent = "";
        els.briefNotifSubtitle.hidden = true;
      }
      if (els.briefNotifDot) {
        els.briefNotifDot.classList.add("has-unread");
        els.briefNotifDot.setAttribute("data-count", String(count));
      }
      els.briefNotif.setAttribute("data-unread", "true");
      els.briefNotif.setAttribute("data-count", String(count));
      if (els.briefNotifBrand) {
        els.briefNotifBrand.innerHTML = spec.svg;
        els.briefNotifBrand.dataset.brand = spec.brand;
        els.briefNotifBrand.hidden = false;
      }
      if (els.briefNotifEmoji) {
        els.briefNotifEmoji.textContent = spec.emoji;
        els.briefNotifEmoji.hidden = true;
      }
      if (els.briefNotifIcon) {
        els.briefNotifIcon.dataset.brand = spec.brand;
        els.briefNotifIcon.classList.remove("has-emoji");
        els.briefNotifIcon.classList.add("has-brand");
      }
      if (els.stage) els.stage.style.setProperty("--notif-brand-color", spec.color);
      els.briefNotif.style.setProperty("--notif-brand-color", spec.color);
    }
    if (els.notifCountBadge) {
      els.notifCountBadge.textContent = String(count);
      els.notifCountBadge.hidden = count === 0;
    }
    if (activeBrief === "notif") {
      syncIslandIllumination({ animate: true });
    }
    requestAnimationFrame(() => {
      if (els.briefNotifTitle) {
        checkAndApplyMarquee(els.briefNotifTitle, { marquee360: true, text: singleLine });
      }
    });
  }

  function renderNotifInbox() {
    const count = notificationInbox.length;
    if (els.notifCountBadge) {
      els.notifCountBadge.textContent = String(count);
      els.notifCountBadge.hidden = count === 0;
    }
    if (els.notifClearAllBtn) {
      els.notifClearAllBtn.hidden = count === 0;
    }
    if (els.stageNotifEmpty) {
      els.stageNotifEmpty.hidden = count > 0 || pendingTasks.length > 0;
    }
    if (!els.stageNotifList) return;

    // Preserve any elements currently executing their dismiss animation
    const dismissingIds = new Set(
      Array.from(els.stageNotifList.querySelectorAll(".notif-item.is-dismissing"))
        .map((el) => Number(el.dataset.notifId))
        .filter(Boolean)
    );

    if (count === 0 && dismissingIds.size === 0) {
      els.stageNotifList.innerHTML = "";
      requestExpandedHeightUpdate();
      return;
    }

    const htmlParts = [];
    for (const notif of notificationInbox) {
      if (dismissingIds.has(notif.id)) continue;
      const spec = getNotificationBrandSpec(notif.app, notif.title);
      const appName = escapeHtml(notif.app || "Sistema");
      const title = escapeHtml(notif.title || "");
      const body = notif.body ? `<p class="notif-item__body">${escapeHtml(notif.body)}</p>` : "";
      const timeStr = formatNotifTime(notif.time);

      htmlParts.push(`
        <div class="notif-item" data-notif-id="${notif.id}">
          <div class="notif-item__head">
            <div class="notif-item__app-meta">
              <span class="notif-item__brand notif-brand-icon" data-brand="${spec.brand}" aria-hidden="true">${spec.svg}</span>
              <span class="notif-item__app">${appName}</span>
            </div>
            <span class="notif-item__time">${timeStr}</span>
          </div>
          <div class="notif-item__content">
            ${title ? `<strong class="notif-item__title">${title}</strong>` : ""}
            ${body}
          </div>
          <div class="notif-item__actions">
            <button type="button" class="notif-btn notif-btn--open" data-action="open" data-id="${notif.id}" title="Abrir aplicación">Abrir</button>
            <button type="button" class="notif-btn notif-btn--dismiss" data-action="dismiss" data-id="${notif.id}" title="Marcar como vista">✕</button>
          </div>
        </div>
      `);
    }

    els.stageNotifList.innerHTML = htmlParts.join("");
    requestExpandedHeightUpdate();
  }

  function sendNotificationAction(id, action) {
    if (id == null) return;
    const numId = Number(id);
    logActivity("notification.action", `${action}:${numId}`);
    if (core.connected) {
      core.send({ type: "user.notification", data: { id: numId, action } });
      return;
    }
    const cfg = coreHttpConfig();
    if (!cfg) return;
    fetch(`${cfg.baseUrl}/v1/system/notifications/${encodeURIComponent(numId)}`, {
      method: "POST",
      headers: { ...cfg.headers, "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    }).catch((err) => reportCoreFetchError(`/v1/system/notifications/${numId}`, err));
  }

  function openNotification(id) {
    if (id == null) return;
    sendNotificationAction(id, "open");
  }

  function dismissNotification(id) {
    if (id == null) return;
    const numId = Number(id);
    sendNotificationAction(numId, "dismiss");

    const itemEl = els.stageNotifList ? els.stageNotifList.querySelector(`[data-notif-id="${numId}"]`) : null;
    if (itemEl && !itemEl.classList.contains("is-dismissing")) {
      itemEl.classList.add("is-dismissing");
      setTimeout(() => {
        onNotificationRemoved({ id: numId });
      }, 300);
    } else {
      onNotificationRemoved({ id: numId });
    }
  }

  function clearAllNotifications() {
    if (notificationInbox.length === 0) return;
    const ids = notificationInbox.map((n) => n.id);
    for (const id of ids) {
      sendNotificationAction(id, "dismiss");
    }
    if (els.stageNotifList) {
      const items = els.stageNotifList.querySelectorAll(".notif-item");
      items.forEach((item) => item.classList.add("is-dismissing"));
    }
    setTimeout(() => {
      notificationInbox.length = 0;
      renderNotifBrief();
      renderNotifInbox();
      if (activeBrief === "notif") {
        clearTimeout(briefPreviewTimer);
        setActiveBrief("avatar");
      }
    }, 320);
  }

  function onNotification(notif) {
    if (!notif || notif.id == null) return;
    const id = Number(notif.id);
    seenNotificationIds.add(id);
    const idx = notificationInbox.findIndex((n) => n.id === id);
    if (idx !== -1) {
      notificationInbox.splice(idx, 1);
    }
    notificationInbox.unshift({
      id,
      app: notif.app || "Sistema",
      title: notif.title || "",
      body: notif.body || "",
      time: typeof notif.time === "number" ? notif.time : Date.now() / 1000,
    });
    renderNotifBrief();
    renderNotifInbox();

    // Living avatar alert reaction with squash & stretch + iluminación de marca en Dynamic Island
    triggerSquashAndStretch();
    const spec = getNotificationBrandSpec(notif.app, notif.title);
    const notifApp = notif.app ? `${notif.app} 🔔` : "Notificación 🔔";
    triggerTransientAvatarReaction({ actionText: notifApp, mood: "surprise", durationMs: 4800 });

    if (!agentWorking && !pendingConfirmId) {
      const notifSummary = [notif.title, notif.body].filter(Boolean).join(" — ") || "Nueva notificación";
      updateAgentDock(notifSummary, {
        tone: "reminder",
        badge: `${spec.emoji} ${notif.app || "Notificación"}`,
        animate: "update",
      });
    }

    previewBrief("notif", 9000);

    const isUserInteracting =
      (els.menu && !els.menu.hidden) ||
      document.activeElement === els.chatInput ||
      Boolean(els.stage?.matches(":hover")) ||
      Boolean(pendingConfirmId) ||
      skinsCardOpen;

    if (pet.autoExpandEvents && !focusActive && !notchExpanded && !isUserInteracting) {
      triggerMomentaryExpansion("hero", 5000);
    } else if (!notchExpanded) {
      triggerIslandSubtlePulse("surprise", notifApp, { pulseKey: "notif", brandColor: spec.color });
    }
    syncIslandIllumination({ animate: true });
  }

  function onNotificationRemoved(data) {
    if (!data || data.id == null) return;
    const id = Number(data.id);
    const idx = notificationInbox.findIndex((n) => n.id === id);
    if (idx !== -1) {
      notificationInbox.splice(idx, 1);
    }
    renderNotifBrief();
    renderNotifInbox();
    if (notificationInbox.length === 0 && activeBrief === "notif") {
      clearTimeout(briefPreviewTimer);
      setActiveBrief("avatar");
    }
  }

  let activeMedia = null;
  let mediaTicker = null;

  const ONE_UI_MEDIA_PALETTES = [
    ["#38bdf8", "#0ea5e9"],
    ["#f43f5e", "#fb923c"],
    ["#34d399", "#06b6d4"],
    ["#818cf8", "#ec4899"],
    ["#f59e0b", "#ef4444"],
    ["#22d3ee", "#3b82f6"],
  ];

  function hashTrackKey(str) {
    let h = 2166136261;
    for (let i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }

  function coreHttpEndpoint(path, wsUrlOverride, tokenOverride) {
    const cfg = coreHttpConfig(wsUrlOverride, tokenOverride);
    if (!cfg) {
      throw new Error("Invalid Core URL");
    }
    return { base: cfg.baseUrl, url: `${cfg.baseUrl}${path}`, headers: cfg.headers, token: cfg.token };
  }

  let activeCoverObjectUrl = null;
  let activeCoverResolveToken = 0;
  let mediaCoverRetryTimer = null;
  let activeCoverTrackKey = "";
  let activeCoverSourceKey = "";
  let activeCoverDisplayUrl = null;
  let activeCoverRetrySourceKey = "";

  function clearMediaCoverRetry() {
    if (mediaCoverRetryTimer) {
      clearTimeout(mediaCoverRetryTimer);
      mediaCoverRetryTimer = null;
    }
    activeCoverRetrySourceKey = "";
  }

  function revokeActiveCoverObjectUrl() {
    if (activeCoverObjectUrl) {
      try {
        URL.revokeObjectURL(activeCoverObjectUrl);
      } catch (_) {}
      activeCoverObjectUrl = null;
    }
  }

  function mediaTrackKey(title = "", artist = "") {
    return `${String(title || "").trim()}|${String(artist || "").trim()}`;
  }

  function applyCoverAccentFromImage(imgEl, fallbackTitle, fallbackArtist) {
    try {
      if (!imgEl || !imgEl.naturalWidth) return;
      const canvas = document.createElement("canvas");
      canvas.width = 10;
      canvas.height = 10;
      const ctx = canvas.getContext("2d", { willReadFrequently: true });
      if (!ctx) return;
      ctx.drawImage(imgEl, 0, 0, 10, 10);
      const { data } = ctx.getImageData(0, 0, 10, 10);
      let r1 = 0;
      let g1 = 0;
      let b1 = 0;
      let count = 0;
      let bestSat = -1;
      let r2 = 56;
      let g2 = 189;
      let b2 = 248;
      for (let i = 0; i < data.length; i += 4) {
        if (data[i + 3] < 40) continue;
        const r = data[i];
        const g = data[i + 1];
        const b = data[i + 2];
        r1 += r;
        g1 += g;
        b1 += b;
        count++;
        const maxC = Math.max(r, g, b);
        const minC = Math.min(r, g, b);
        const sat = maxC - minC + (maxC > 65 ? 24 : 0);
        if (sat > bestSat) {
          bestSat = sat;
          r2 = Math.min(255, Math.round(r * 1.15 + 24));
          g2 = Math.min(255, Math.round(g * 1.15 + 24));
          b2 = Math.min(255, Math.round(b * 1.15 + 24));
        }
      }
      if (!count) return;
      const avgR = Math.min(255, Math.round((r1 / count) * 1.12 + 28));
      const avgG = Math.min(255, Math.round((g1 / count) * 1.12 + 28));
      const avgB = Math.min(255, Math.round((b1 / count) * 1.12 + 28));
      const c1 = `rgb(${r2}, ${g2}, ${b2})`;
      const c2 = `rgb(${avgR}, ${avgG}, ${avgB})`;
      activeMediaAccents = [c1, c2];
      for (const target of [els.stage, els.mediaWidget, els.briefMedia]) {
        if (!target) continue;
        target.style.setProperty("--media-accent", c1);
        target.style.setProperty("--media-accent-2", c2);
      }
      syncIslandIllumination({ animate: activeBrief === "media" });
    } catch {
      applyMediaPalette(fallbackTitle, fallbackArtist);
    }
  }

  function applyMediaCoverVisuals(coverUrl, { title = "", artist = "", playing = false } = {}) {
    const coverImgs = [els.mediaCoverImg, els.mediaCoverBackdropImg, els.briefMediaCover].filter(Boolean);
    const briefIcon = els.briefMediaIcon || $("briefMediaIcon");
    const discIcon = els.mediaDiscIcon || $("mediaDiscIcon");
    const showGlassBlur = Boolean(coverUrl && playing);

    if (!coverUrl) {
      for (const img of coverImgs) {
        img.hidden = true;
        img.removeAttribute("src");
        img.removeAttribute("crossorigin");
      }
      if (els.stageGlassCoverBlur) {
        els.stageGlassCoverBlur.hidden = true;
        els.stageGlassCoverBlur.removeAttribute("src");
        els.stageGlassCoverBlur.removeAttribute("crossorigin");
      }
      if (discIcon) discIcon.hidden = false;
      if (briefIcon) briefIcon.hidden = false;
      els.mediaArtworkWrap?.classList.remove("has-cover");
      els.briefMedia?.classList.remove("has-cover");
      return;
    }

    const isLocalUrl = coverUrl.startsWith("blob:") || coverUrl.startsWith("data:");
    const coreBase = (() => {
      try { return coreHttpEndpoint("").base; } catch { return ""; }
    })();
    const useAnonymousCors = !isLocalUrl && Boolean(coreBase && coverUrl.startsWith(coreBase));

    for (const img of coverImgs) {
      if (useAnonymousCors) {
        img.crossOrigin = "anonymous";
      } else {
        img.removeAttribute("crossorigin");
      }
      img.onload = () => {
        img.hidden = false;
        if (img === els.briefMediaCover) {
          if (briefIcon) briefIcon.hidden = true;
          els.briefMedia?.classList.add("has-cover");
        }
        if (img === els.mediaCoverImg) {
          if (discIcon) discIcon.hidden = true;
          els.mediaArtworkWrap?.classList.add("has-cover");
          applyCoverAccentFromImage(img, title, artist);
        }
      };
      img.onerror = () => {
        img.hidden = true;
        img.removeAttribute("src");
        if (img === els.mediaCoverImg) {
          els.mediaArtworkWrap?.classList.remove("has-cover");
          if (discIcon) discIcon.hidden = false;
          applyMediaPalette(title, artist);
        }
        if (img === els.briefMediaCover) {
          els.briefMedia?.classList.remove("has-cover");
          if (briefIcon) briefIcon.hidden = false;
        }
      };
      if (img.getAttribute("src") !== coverUrl) {
        img.src = coverUrl;
        img.hidden = false;
        if (img === els.briefMediaCover) {
          if (briefIcon) briefIcon.hidden = true;
          els.briefMedia?.classList.add("has-cover");
        }
        if (img === els.mediaCoverImg) {
          if (discIcon) discIcon.hidden = true;
          els.mediaArtworkWrap?.classList.add("has-cover");
        }
      } else {
        img.hidden = false;
        if (img.complete && img.naturalWidth > 0) {
          if (img === els.briefMediaCover) {
            if (briefIcon) briefIcon.hidden = true;
            els.briefMedia?.classList.add("has-cover");
          }
          if (img === els.mediaCoverImg) {
            if (discIcon) discIcon.hidden = true;
            els.mediaArtworkWrap?.classList.add("has-cover");
            applyCoverAccentFromImage(img, title, artist);
          }
        }
      }
    }

    if (els.stageGlassCoverBlur) {
      if (useAnonymousCors) {
        els.stageGlassCoverBlur.crossOrigin = "anonymous";
      } else {
        els.stageGlassCoverBlur.removeAttribute("crossorigin");
      }
      if (els.stageGlassCoverBlur.getAttribute("src") !== coverUrl) {
        els.stageGlassCoverBlur.src = coverUrl;
      }
      els.stageGlassCoverBlur.hidden = !showGlassBlur;
    }
  }

  function resolveMediaCoverCandidate(d) {
    if (!d || typeof d !== "object") return null;
    const raw =
      d.cover ??
      d.artwork ??
      d.thumbnail ??
      d.album_art ??
      d.cover_url ??
      d.image ??
      d.art ??
      d.cover_path;

    const coreBase = (() => {
      try { return coreHttpEndpoint("").base; } catch { return ""; }
    })();

    if (typeof raw === "string" && raw.trim()) {
      const s = raw.trim();
      if (s.startsWith("data:") || s.startsWith("http://") || s.startsWith("https://") || s.startsWith("blob:")) {
        const isCoreArtwork = Boolean(coreBase && s.startsWith(`${coreBase}/v1/`));
        return { url: s, needsAuth: false, isCoreArtwork };
      }
      if (s.startsWith("/")) {
        try {
          const ep = coreHttpEndpoint(s);
          return { url: ep.url, needsAuth: Boolean(ep.token), isCoreArtwork: true };
        } catch {
          return null;
        }
      }
      return { url: `data:image/jpeg;base64,${s}`, needsAuth: false, isCoreArtwork: false };
    }

    if (raw && typeof raw === "object") {
      const urlVal = raw.url || raw.src || raw.href;
      if (typeof urlVal === "string" && urlVal.trim()) {
        return resolveMediaCoverCandidate({ cover: urlVal });
      }
      const b64 = raw.data || raw.base64;
      if (typeof b64 === "string" && b64.trim()) {
        const mime = raw.mime || raw.content_type || "image/jpeg";
        const val = b64.startsWith("data:") ? b64 : `data:${mime};base64,${b64}`;
        return { url: val, needsAuth: false, isCoreArtwork: false };
      }
    }

    if (d.has_cover === true || (d.title && d.title !== "Sin título")) {
      try {
        const ep = coreHttpEndpoint("/v1/system/media/artwork");
        return { url: ep.url, needsAuth: Boolean(ep.token), isCoreArtwork: true };
      } catch {
        return null;
      }
    }
    return null;
  }

  async function syncMediaCover(d, { title = "", artist = "", playing = false } = {}, attempt = 0) {
    if (!d || (!title && !playing && !d.artwork && !d.cover)) {
      clearMediaCoverRetry();
      activeCoverResolveToken++;
      activeCoverTrackKey = "";
      activeCoverSourceKey = "";
      activeCoverDisplayUrl = null;
      applyMediaCoverVisuals(null, { title, artist, playing });
      revokeActiveCoverObjectUrl();
      return;
    }

    const trackKey = mediaTrackKey(title, artist);
    if (trackKey !== activeCoverTrackKey) {
      clearMediaCoverRetry();
      activeCoverTrackKey = trackKey;
      activeCoverSourceKey = "";
      activeCoverDisplayUrl = null;
      applyMediaCoverVisuals(null, { title, artist, playing });
      revokeActiveCoverObjectUrl();
    }

    const candidate = resolveMediaCoverCandidate(d);
    if (!candidate) {
      clearMediaCoverRetry();
      activeCoverResolveToken++;
      activeCoverSourceKey = "";
      activeCoverDisplayUrl = null;
      applyMediaCoverVisuals(null, { title, artist, playing });
      revokeActiveCoverObjectUrl();
      return;
    }

    const sourceKey = `${trackKey}::${candidate.url}`;
    if (attempt === 0) {
      if (activeCoverSourceKey === sourceKey && activeCoverDisplayUrl) {
        applyMediaCoverVisuals(activeCoverDisplayUrl, { title, artist, playing });
        return;
      }
      if (activeCoverRetrySourceKey === sourceKey && mediaCoverRetryTimer) {
        return;
      }
      clearMediaCoverRetry();
    }

    const resolveId = ++activeCoverResolveToken;
    const coreBase = (() => {
      try { return coreHttpEndpoint("").base; } catch { return ""; }
    })();
    const isCoreUrl = Boolean(
      candidate.isCoreArtwork ||
      (coreBase && candidate.url.startsWith(`${coreBase}/v1/`))
    );

    if (!isCoreUrl && !candidate.needsAuth) {
      activeCoverSourceKey = sourceKey;
      activeCoverDisplayUrl = candidate.url;
      applyMediaCoverVisuals(candidate.url, { title, artist, playing });
      revokeActiveCoverObjectUrl();
      return;
    }

    const isSameActiveTrack = () =>
      Boolean(activeMedia) && mediaTrackKey(activeMedia.title, activeMedia.artist) === trackKey;
    const RETRY_DELAYS_MS = [900, 2200];

    const handleCoreMiss = async (networkFailure = false) => {
      if (resolveId !== activeCoverResolveToken || !isSameActiveTrack()) return;

      if (attempt < RETRY_DELAYS_MS.length) {
        activeCoverRetrySourceKey = sourceKey;
        mediaCoverRetryTimer = setTimeout(() => {
          mediaCoverRetryTimer = null;
          activeCoverRetrySourceKey = "";
          if (!isSameActiveTrack()) return;
          syncMediaCover(
            d,
            {
              title: activeMedia?.title ?? title,
              artist: activeMedia?.artist ?? artist,
              playing: Boolean(activeMedia?.playing),
            },
            attempt + 1
          );
        }, RETRY_DELAYS_MS[attempt]);
      }

      if (!activeCoverDisplayUrl && (attempt >= RETRY_DELAYS_MS.length || (networkFailure && !core.connected))) {
        applyMediaCoverVisuals(null, { title, artist, playing });
      }
    };

    try {
      const ep = coreHttpEndpoint("");
      let fetchUrl = candidate.url;
      if (isCoreUrl && !fetchUrl.includes("?")) {
        fetchUrl = `${fetchUrl}?t=${encodeURIComponent(trackKey)}_${attempt}`;
      }
      const res = await fetch(fetchUrl, { headers: ep.headers, mode: "cors", cache: "no-store" });
      if (resolveId !== activeCoverResolveToken) return;
      if (!res.ok) {
        await handleCoreMiss(false);
        return;
      }
      const blob = await res.blob();
      if (resolveId !== activeCoverResolveToken) return;
      if (!blob || blob.size === 0) {
        await handleCoreMiss(false);
        return;
      }
      clearMediaCoverRetry();
      const nextObjectUrl = URL.createObjectURL(blob);
      const prevObjectUrl = activeCoverObjectUrl;
      activeCoverObjectUrl = nextObjectUrl;
      activeCoverSourceKey = sourceKey;
      activeCoverDisplayUrl = nextObjectUrl;
      applyMediaCoverVisuals(nextObjectUrl, {
        title,
        artist,
        playing: Boolean(activeMedia?.playing ?? playing),
      });
      if (prevObjectUrl && prevObjectUrl !== nextObjectUrl) {
        try {
          URL.revokeObjectURL(prevObjectUrl);
        } catch (_) {}
      }
    } catch (err) {
      console.warn("[MEKA] No se pudo cargar la carátula multimedia:", err);
      if (resolveId === activeCoverResolveToken) {
        await handleCoreMiss(true);
      }
    }
  }

  function applyMediaPalette(title = "", artist = "") {
    const hasTrack = Boolean(title || artist);
    const key = `${title || ""}|${artist || ""}`;
    const palette = hasTrack
      ? ONE_UI_MEDIA_PALETTES[hashTrackKey(key) % ONE_UI_MEDIA_PALETTES.length]
      : ONE_UI_MEDIA_PALETTES[0];
    const [accent1, accent2] = palette;
    activeMediaAccents = [accent1, accent2];
    for (const target of [els.stage, els.mediaWidget, els.briefMedia]) {
      if (!target) continue;
      target.style.setProperty("--media-accent", accent1);
      target.style.setProperty("--media-accent-2", accent2);
    }
    syncIslandIllumination({ animate: activeBrief === "media" });
  }

  function formatTime(sec) {
    if (!Number.isFinite(sec) || sec < 0) return "0:00";
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  }
  const fmtSec = formatTime;

  function renderMediaProgress() {
    if (!activeMedia || !els.mediaWidget) return;
    const pos = activeMedia.position || 0;
    const dur = activeMedia.duration || 0;
    const pct = dur > 0 ? Math.min(100, Math.max(0, (pos / dur) * 100)) : 0;
    const pctStr = `${pct.toFixed(2)}%`;
    const posStr = fmtSec(pos);
    const durStr = fmtSec(dur);
    if (els.mediaBarFill) els.mediaBarFill.style.inlineSize = pctStr;
    if (els.mediaProgressNative) els.mediaProgressNative.value = pct;
    els.mediaBar?.style.setProperty("--media-progress", pctStr);
    if (els.mediaTimeCurrent) els.mediaTimeCurrent.textContent = posStr;
    if (els.mediaTimeTotal) els.mediaTimeTotal.textContent = durStr;
    if (els.mediaTime) els.mediaTime.textContent = `${posStr} / ${durStr}`;
  }

  function startMediaTicker() {
    stopMediaTicker();
    if (!activeMedia || !activeMedia.playing) return;
    mediaTicker = setInterval(() => {
      if (activeMedia && activeMedia.playing) {
        activeMedia.position = (activeMedia.position || 0) + 1;
        if (activeMedia.duration && activeMedia.position > activeMedia.duration) {
          activeMedia.position = activeMedia.duration;
        }
        renderMediaProgress();
      }
    }, 1000);
  }

  function stopMediaTicker() {
    if (mediaTicker) {
      clearInterval(mediaTicker);
      mediaTicker = null;
    }
  }

  function applySystemMedia(d) {
    const wasPlaying = Boolean(activeMedia?.playing);
    const nowPlaying = Boolean(d?.playing);

    if (!d || (!d.title && !d.playing)) {
      activeMedia = null;
      clearMediaCoverRetry();
      if (userPinnedBrief === "media") {
        clearTimeout(userPinnedBriefTimer);
        userPinnedBriefTimer = null;
        userPinnedBrief = null;
      }
      if (activeBrief === "media") {
        clearTimeout(briefPreviewTimer);
        setActiveBrief("avatar", { syncView: false });
      }
      stopMediaTicker();
      if (isMusicReactivity) {
        isMusicReactivity = false;
        musicActiveLabel = null;
        if (!agentWorking && !pet.sleeping) {
          setBase("idle", { interrupt: true });
          show("idle");
          updateStageBadges();
        }
      }
      // ITEM 3: Equalizer bars never display in the avatar brief (#briefAvatar)
      if (els.miniMusicBar) els.miniMusicBar.hidden = true;
      if (els.mediaWidget) {
        els.mediaWidget.hidden = (stageView !== "media");
        els.mediaWidget.dataset.playing = "false";
        els.mediaWidget.setAttribute("data-media-playing", "false");
        els.mediaWidget.classList.remove("is-playing");
      }
      if (els.stage) {
        els.stage.setAttribute("data-media-playing", "false");
        els.stage.classList.remove("is-playing-media");
        clearIslandMediaGlow();
      }
      applyMediaPalette("", "");
      syncMediaCover(null);
      if (els.mediaTitle) els.mediaTitle.textContent = "Sin reproducción";
      if (els.mediaArtist) els.mediaArtist.textContent = "—";
      if (els.mediaAlbum) {
        els.mediaAlbum.textContent = "";
        els.mediaAlbum.hidden = true;
      }
      if (els.mediaDot) els.mediaDot.hidden = true;
      if (els.mediaBarFill) els.mediaBarFill.style.inlineSize = "0%";
      if (els.mediaProgressNative) els.mediaProgressNative.value = 0;
      els.mediaBar?.style.setProperty("--media-progress", "0%");
      if (els.mediaTimeCurrent) els.mediaTimeCurrent.textContent = "0:00";
      if (els.mediaTimeTotal) els.mediaTimeTotal.textContent = "0:00";
      if (els.mediaTime) els.mediaTime.textContent = "0:00 / 0:00";
      if (els.mediaPlayPause) {
        els.mediaPlayPause.classList.remove("is-playing");
        els.mediaPlayPause.dataset.playing = "false";
        els.mediaPlayPause.setAttribute("aria-label", "Reproducir o pausar");
        if (!els.mediaPlayPause.querySelector("svg")) {
          els.mediaPlayPause.textContent = "▶";
        }
      }
      if (els.briefMediaTitle) {
        els.briefMediaTitle.textContent = "Sin reproducción";
        checkAndApplyMarquee(els.briefMediaTitle, { marquee360: true, text: "Sin reproducción" });
      }
      if (els.briefMediaArtist) {
        els.briefMediaArtist.textContent = "";
        els.briefMediaArtist.hidden = true;
      }
      if (els.briefWaveform) {
        els.briefWaveform.setAttribute("data-playing", "false");
        els.briefWaveform.classList.remove("is-playing");
      }
      if (els.briefMedia) {
        els.briefMedia.removeAttribute("data-media-playing");
      }
      syncIslandIllumination({ animate: true });
      return;
    }

    const prevTitle = activeMedia?.title;
    const prevArtist = activeMedia?.artist;
    const hadMediaBefore = Boolean(activeMedia && activeMedia.title && activeMedia.title !== "Sin título");
    const isNewTrack = !hadMediaBefore || (d.title && d.title !== prevTitle) || (d.artist && d.artist !== prevArtist);
    const justStartedPlaying = nowPlaying && !wasPlaying;
    const justDetectedPlayer = !hadMediaBefore && Boolean(d.title && d.title !== "Sin título");

    activeMedia = {
      playing: Boolean(d.playing),
      title: d.title || "Sin título",
      artist: d.artist || "",
      album: d.album || "",
      app: d.app || "Música",
      artwork: d.artwork !== undefined ? d.artwork : (!isNewTrack ? activeMedia?.artwork : null),
      cover: d.cover !== undefined ? d.cover : (!isNewTrack ? activeMedia?.cover : null),
      position: typeof d.position === "number" ? d.position : (activeMedia?.position || 0),
      duration: typeof d.duration === "number" ? d.duration : (activeMedia?.duration || 0),
    };

    applyMediaPalette(activeMedia.title, activeMedia.artist);
    syncMediaCover(
      {
        ...d,
        title: activeMedia.title,
        artist: activeMedia.artist,
        artwork: activeMedia.artwork,
        cover: activeMedia.cover,
      },
      {
        title: activeMedia.title,
        artist: activeMedia.artist,
        playing: activeMedia.playing,
      }
    );

    // Living avatar music reactivity:
    // Animación y etiqueta breve al iniciar reproducción o cambiar de canción; vuelve a estado normal tras 4.5s
    if (nowPlaying && (!wasPlaying || isNewTrack)) {
      const musicLabel = pick(["Escuchando música 🎶", "Bailando 🎵"]);
      const danceState = (skin().states && skin().states.dance) ? "dance" : "happy";
      triggerTransientAvatarReaction({ actionText: musicLabel, mood: danceState, durationMs: 4500 });
    } else if (!nowPlaying && wasPlaying) {
      clearIslandMediaGlow();
      if (transientEventAction) {
        clearTimeout(transientEventTimer);
        transientEventAction = null;
        if (!agentWorking && !pet.sleeping) {
          setBase("idle", { interrupt: true });
          show("idle");
        }
        updateStageBadges();
      }
    }

    // ITEM 3: Audio equalizer bars never display in the avatar brief (#briefAvatar)
    if (els.miniMusicBar) {
      els.miniMusicBar.hidden = true;
    }

    // ITEM 1: Format title + artist as a single line (e.g. Di Que Sí · Grupo Marca Registrada)
    const singleLine = activeMedia.artist
      ? `${activeMedia.title} · ${activeMedia.artist}`
      : activeMedia.title;

    if (els.briefMediaTitle) {
      requestAnimationFrame(() => {
        checkAndApplyMarquee(els.briefMediaTitle, { marquee360: true, text: singleLine });
      });
    }
    if (els.briefMediaArtist) {
      els.briefMediaArtist.textContent = "";
      els.briefMediaArtist.hidden = true;
    }

    if (els.briefWaveform) {
      els.briefWaveform.setAttribute("data-playing", String(activeMedia.playing));
      els.briefWaveform.classList.toggle("is-playing", activeMedia.playing);
    }
    if (els.briefMedia) {
      els.briefMedia.setAttribute("data-media-playing", String(activeMedia.playing));
    }

    if (isNewTrack && hadMediaBefore && userPinnedBrief === "avatar") {
      clearTimeout(userPinnedBriefTimer);
      userPinnedBriefTimer = null;
      userPinnedBrief = null;
    }

    // ITEM 2 + T-061: Preview en píldora y expansión momentánea al detectar reproductor, reproducir o cambiar de canción
    if ((isNewTrack || justStartedPlaying || justDetectedPlayer) && activeMedia.title && activeMedia.title !== "Sin título") {
      previewBrief("media", 9000);
      if (!agentWorking && !pendingConfirmId) {
        updateAgentDock(singleLine, {
          tone: "idle",
          badge: `🎶 ${activeMedia.app || "Música"}`,
          animate: "update",
        });
      }
      const shouldMomentaryExpand = activeMedia.playing || (isNewTrack && hadMediaBefore);
      const isUserInteracting =
        (els.menu && !els.menu.hidden) ||
        document.activeElement === els.chatInput ||
        Boolean(els.stage?.matches(":hover")) ||
        Boolean(pendingConfirmId) ||
        skinsCardOpen;
      if (pet.autoExpandEvents && shouldMomentaryExpand && !focusActive && !notchExpanded && !isUserInteracting) {
        triggerMomentaryExpansion("hero", 5000);
      } else if (!notchExpanded && shouldMomentaryExpand) {
        const danceMood = (skin().states && skin().states.dance) ? "dance" : "happy";
        triggerIslandSubtlePulse(danceMood, activeBrief === "avatar" ? singleLine : "", { pulseKey: "media" });
        triggerIslandMediaGlow(singleLine);
      }
    }

    if (els.stage) {
      els.stage.setAttribute("data-media-playing", String(activeMedia.playing));
      els.stage.classList.toggle("is-playing-media", activeMedia.playing);
    }
    if (els.mediaWidget) {
      els.mediaWidget.hidden = (stageView !== "media");
      els.mediaWidget.dataset.playing = String(activeMedia.playing);
      els.mediaWidget.setAttribute("data-media-playing", String(activeMedia.playing));
      els.mediaWidget.classList.toggle("is-playing", activeMedia.playing);
      const sourceText = String(activeMedia.app || "Música").replace(/^🎵\s*/, "").trim() || "Música";
      const clippedSource = sourceText.length > 14 ? sourceText.slice(0, 12) + "…" : sourceText;
      if (els.mediaSource) els.mediaSource.textContent = clippedSource;
      if (els.mediaApp && els.mediaApp !== els.mediaSource) els.mediaApp.textContent = clippedSource;
      if (els.mediaTitle) els.mediaTitle.textContent = activeMedia.title;
      if (els.mediaArtist) els.mediaArtist.textContent = activeMedia.artist || "Reproductor";
      if (els.mediaAlbum) {
        const albumTxt = String(activeMedia.album || "").trim();
        els.mediaAlbum.textContent = albumTxt;
        els.mediaAlbum.hidden = !albumTxt;
      }
      if (els.mediaDot) els.mediaDot.hidden = !activeMedia.artist;
      if (els.mediaPlayPause) {
        els.mediaPlayPause.classList.toggle("is-playing", activeMedia.playing);
        els.mediaPlayPause.dataset.playing = String(activeMedia.playing);
        els.mediaPlayPause.setAttribute("aria-label", activeMedia.playing ? "Pausar" : "Reproducir");
        if (!els.mediaPlayPause.querySelector("svg")) {
          els.mediaPlayPause.textContent = activeMedia.playing ? "⏸" : "▶";
        }
      }
      renderMediaProgress();
      requestAnimationFrame(() => {
        if (els.mediaTitle) checkAndApplyMarquee(els.mediaTitle);
        if (els.mediaArtist) checkAndApplyMarquee(els.mediaArtist);
      });
    }

    if (activeMedia.playing) {
      startMediaTicker();
    } else {
      stopMediaTicker();
    }
    syncIslandIllumination({ animate: true });
  }
  const updateMedia = applySystemMedia;

  function updateBattery(d) {
    if (!d || typeof d.percent !== "number") return;
    const isCharging = Boolean(d.charging);
    const pct = Math.round(d.percent);

    // ITEM 4: Discreet battery update: never render bulky center chips
    if (els.hudBatteryChip) {
      els.hudBatteryChip.hidden = true;
    }

    // Update #headerBattery in top header
    const headerBat = $("headerBattery") || els.headerBattery;
    const headerBatIcon = $("headerBatteryIcon");
    const headerBatText = $("headerBatteryText");
    if (headerBat) {
      headerBat.hidden = false;
      const icon = isCharging ? "⚡" : (pct <= 20 ? "🪫" : "🔋");
      if (headerBatIcon && headerBatText) {
        headerBatIcon.textContent = icon;
        headerBatText.textContent = `${pct}%`;
      } else {
        headerBat.textContent = `${icon} ${pct}%`;
      }
      headerBat.title = `Batería: ${pct}%${isCharging ? " (Cargando)" : ""}`;
      if (isCharging) {
        headerBat.style.color = "#30d158";
      } else if (pct <= 20) {
        headerBat.style.color = "#ff453a";
      } else {
        headerBat.style.removeProperty("color");
      }
    }
  }

  function sendMediaAction(action) {
    logActivity("media.action", action);
    if (core.connected) {
      core.send({ type: "user.media", data: { action } });
      return;
    }
    const cfg = coreHttpConfig();
    if (!cfg) return;
    fetch(`${cfg.baseUrl}/v1/system/media`, {
      method: "POST",
      headers: { ...cfg.headers, "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    }).catch((err) => reportCoreFetchError("/v1/system/media", err));
  }

  // ------------------------------------------------------------------ Modo Concentración (T-051 · Contrato 1.9 · Interruptor sin temporizador)

  function stopFocusRenewal() {
    if (focusRenewTimer) {
      clearInterval(focusRenewTimer);
      focusRenewTimer = null;
    }
    if (focusInterval) {
      clearInterval(focusInterval);
      focusInterval = null;
    }
  }

  function renewFocusSilently() {
    if (!focusActive) return;
    if (core.connected) {
      core.send({ type: "user.focus", data: { action: "start", minutes: 240 } });
      return;
    }
    const cfg = coreHttpConfig();
    if (cfg) {
      fetch(`${cfg.baseUrl}/v1/focus`, {
        method: "POST",
        headers: { ...cfg.headers, "Content-Type": "application/json" },
        body: JSON.stringify({ minutes: 240 }),
      }).catch((err) => reportCoreFetchError("POST /v1/focus (renovación)", err));
    }
  }

  function scheduleFocusRenewal() {
    stopFocusRenewal();
    if (!focusActive) return;
    focusRenewTimer = setInterval(() => {
      if (!focusActive) {
        stopFocusRenewal();
        return;
      }
      renewFocusSilently();
    }, FOCUS_RENEW_MS);
  }

  function updateFocusUI() {
    const badge = $("focusBadge") || els.focusBadge;
    const timerText = $("focusTimerText") || els.focusTimerText;
    const toggleBtn = $("focusToggleBtn") || els.focusToggleBtn;
    const cardSwitchBtn = $("focusCardSwitchBtn") || els.focusCardSwitchBtn;
    const cardSwitchLabel = $("focusCardSwitchLabel") || els.focusCardSwitchLabel;

    if (els.stage) {
      els.stage.classList.toggle("is-focus-active", focusActive);
      els.stage.dataset.focus = String(focusActive);
    }

    if (badge) badge.hidden = !focusActive;
    if (timerText) {
      timerText.textContent = "Concentración";
    } else if (badge && focusActive) {
      badge.textContent = "🎯 Concentración";
    }

    if (toggleBtn) {
      toggleBtn.classList.toggle("is-active", focusActive);
      toggleBtn.setAttribute("aria-checked", String(focusActive));
      toggleBtn.removeAttribute("aria-pressed");
    }
    if (cardSwitchBtn) {
      cardSwitchBtn.classList.toggle("is-active", focusActive);
      cardSwitchBtn.setAttribute("aria-checked", String(focusActive));
    }
    if (cardSwitchLabel) {
      cardSwitchLabel.textContent = focusActive ? "Activado" : "Desactivado";
    }
    updateStageBadges();
  }

  function handleFocusStarted(d = {}) {
    focusActive = true;
    const mins = Number(d.minutes) > 0 ? Number(d.minutes) : 240;
    focusUntil = typeof d.until === "number" && d.until > 0
      ? d.until
      : (Date.now() / 1000) + mins * 60;
    const summaryEl = els.focusSummaryText || $("focusSummaryText");
    if (summaryEl) summaryEl.hidden = true;

    updateFocusUI();
    scheduleFocusRenewal();
    requestExpandedHeightUpdate();
  }

  async function refreshNotificationsFromCore() {
    try {
      const cfg = coreHttpConfig();
      if (!cfg) return;
      const notifRes = await fetch(`${cfg.baseUrl}/v1/system/notifications`, { headers: cfg.headers });
      if (notifRes.ok) {
        const notifData = await notifRes.json();
        const list = Array.isArray(notifData.notifications) ? notifData.notifications : [];
        notificationInbox.length = 0;
        for (const item of list) {
          notificationInbox.push(item);
        }
        renderNotifBrief();
        renderNotifInbox();
      } else {
        console.warn(`[MEKA] /v1/system/notifications respondió HTTP ${notifRes.status}`);
      }
    } catch (err) {
      reportCoreFetchError("/v1/system/notifications", err);
    }
  }

  function handleFocusEnded(d = {}) {
    focusActive = false;
    focusUntil = null;
    stopFocusRenewal();
    updateFocusUI();
    const summaryMsg = `Mientras te concentrabas: ${d.notifications || 0} notificaciones ✨`;
    const summaryEl = els.focusSummaryText || $("focusSummaryText");
    if (summaryEl) {
      summaryEl.textContent = summaryMsg;
      summaryEl.hidden = false;
    }
    say(summaryMsg, {
      directToDock: true,
      dockTone: "idle",
      dockBadge: "🎯 Concentración",
      forceExpand: Boolean(pet.autoExpandEvents),
      pulseState: "celebrate",
      pulseText: summaryMsg,
    });
    refreshNotificationsFromCore();
    requestExpandedHeightUpdate();
  }

  function startFocus() {
    const now = Date.now();
    if (now - lastFocusToggleAt < 350) return;
    lastFocusToggleAt = now;

    const mins = 240;
    logActivity("user.focus", `start:${mins}m`);
    if (core.connected) {
      core.send({ type: "user.focus", data: { action: "start", minutes: mins } });
      return;
    }

    handleFocusStarted({ until: (Date.now() / 1000) + mins * 60, minutes: mins });
    const cfg = coreHttpConfig();
    if (cfg) {
      fetch(`${cfg.baseUrl}/v1/focus`, {
        method: "POST",
        headers: { ...cfg.headers, "Content-Type": "application/json" },
        body: JSON.stringify({ minutes: mins }),
      })
        .then((res) => {
          if (!res.ok) {
            console.warn(`[MEKA] POST /v1/focus respondió HTTP ${res.status}`);
            return null;
          }
          return res.json();
        })
        .then((data) => {
          if (data && data.active && !focusActive) {
            handleFocusStarted({ until: data.until, minutes: mins });
          }
        })
        .catch((err) => reportCoreFetchError("POST /v1/focus", err));
    }
  }

  function stopFocus() {
    const now = Date.now();
    if (now - lastFocusToggleAt < 350) return;
    lastFocusToggleAt = now;

    logActivity("user.focus", "stop");
    stopFocusRenewal();
    if (core.connected) {
      core.send({ type: "user.focus", data: { action: "stop" } });
      return;
    }

    if (focusActive) {
      handleFocusEnded({ reason: "user", held: 0, notifications: 0 });
    }
    const cfg = coreHttpConfig();
    if (cfg) {
      fetch(`${cfg.baseUrl}/v1/focus`, {
        method: "DELETE",
        headers: cfg.headers,
      })
        .then((res) => {
          if (!res.ok) {
            console.warn(`[MEKA] DELETE /v1/focus respondió HTTP ${res.status}`);
            return null;
          }
          return res.json();
        })
        .then((data) => {
          if (data && focusActive) {
            handleFocusEnded(data);
          }
        })
        .catch((err) => reportCoreFetchError("DELETE /v1/focus", err));
    }
  }

  async function fetchFocusStatus(wsUrl, token = "") {
    try {
      const cfg = coreHttpConfig(wsUrl, token);
      if (!cfg) return;
      const res = await fetch(`${cfg.baseUrl}/v1/focus`, { headers: cfg.headers });
      if (res.ok) {
        const data = await res.json();
        if (data && data.active && data.until) {
          handleFocusStarted({ until: data.until, minutes: 240 });
        }
      } else {
        console.warn(`[MEKA] GET /v1/focus respondió HTTP ${res.status}`);
      }
    } catch (err) {
      reportCoreFetchError("GET /v1/focus", err);
    }
  }

  // ------------------------------------------------------------------ Hanna Proactiva & Agenda (T-057 · Contrato 1.10)

  function clearMomentaryExpansionTimer() {
    if (momentaryExpandTimer) {
      clearTimeout(momentaryExpandTimer);
      momentaryExpandTimer = null;
    }
  }

  function scheduleMomentaryCollapse(delayMs) {
    clearMomentaryExpansionTimer();
    momentaryExpandTimer = setTimeout(() => {
      momentaryExpandTimer = null;
      if (!wasCollapsedBeforeMomentary) return;
      if (els.stage?.matches(":hover") || !canAutoCollapse()) {
        return;
      }
      hideProactiveAlert();
      wasCollapsedBeforeMomentary = false;
      setNotchExpanded(false);
    }, delayMs);
  }

  function triggerMomentaryExpansion(targetView = "hero", durationMs = 8500) {
    clearMomentaryExpansionTimer();
    clearTimeout(notchCollapseTimer);
    clearTimeout(notchAutoExpandTimer);

    if (!notchExpanded) {
      wasCollapsedBeforeMomentary = true;
      setNotchExpanded(true, { view: targetView, silent: true });
    } else if (!skinsCardOpen && stageView !== targetView) {
      setStageView(targetView);
    }

    if (wasCollapsedBeforeMomentary) {
      momentaryCollapseAt = Date.now() + durationMs;
      scheduleMomentaryCollapse(durationMs);
    }
  }

  function showProactiveAlert({
    kind = "nudge",
    taskId = null,
    title = "",
    kicker = "💡 Hanna Proactiva",
    icon = "✨",
    showTaskActions = false,
    mood = null,
    skipPulse = false,
  } = {}) {
    activeProactiveAlert = {
      kind,
      taskId: taskId != null ? Number(taskId) : null,
      title,
    };
    if (els.proactiveBanner) {
      els.proactiveBanner.dataset.kind = kind;
      els.proactiveBanner.hidden = false;
    }
    if (els.proactiveBannerIcon) els.proactiveBannerIcon.textContent = icon || "✨";
    if (els.proactiveBannerKicker) els.proactiveBannerKicker.textContent = kicker || "Hanna Proactiva";
    if (els.proactiveBannerTitle) els.proactiveBannerTitle.textContent = title || "";
    if (els.proactiveBannerActions) {
      els.proactiveBannerActions.hidden = !(showTaskActions && activeProactiveAlert.taskId != null);
    }

    const targetMood = mood || (kind === "reminder" ? "surprise" : (kind === "welcome" ? "greet" : "happy"));
    setState(targetMood);
    spawnParticles(targetMood === "surprise" ? "❗" : (targetMood === "greet" ? "👋" : "✨"), 4);
    if (pet.autoExpandEvents && !focusActive && !notchExpanded) {
      triggerMomentaryExpansion("hero", 9000);
    } else if (!notchExpanded && !skipPulse) {
      triggerIslandSubtlePulse(targetMood, title);
    }
    requestExpandedHeightUpdate();
  }

  function hideProactiveAlert() {
    activeProactiveAlert = null;
    if (els.proactiveBanner) {
      els.proactiveBanner.hidden = true;
      delete els.proactiveBanner.dataset.kind;
    }
    requestExpandedHeightUpdate();
  }

  function formatTaskDue(dueAt, remindAt) {
    const ts = dueAt ?? remindAt;
    if (!ts || !Number.isFinite(Number(ts))) return "Sin fecha";
    const ms = Number(ts) * 1000;
    const date = new Date(ms);
    if (isNaN(date.getTime())) return "Sin fecha";
    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const taskDayStart = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
    const dayDiff = Math.round((taskDayStart - todayStart) / 86_400_000);
    const timeStr = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    let label;
    if (dayDiff === 0) label = `Hoy ${timeStr}`;
    else if (dayDiff === 1) label = `Mañana ${timeStr}`;
    else if (dayDiff === -1) label = `Ayer ${timeStr}`;
    else {
      const dateStr = date.toLocaleDateString("es-ES", { day: "numeric", month: "short" });
      label = `${dateStr} ${timeStr}`;
    }
    return ms < Date.now() ? `Vencida · ${label}` : label;
  }

  function renderPendingTasks() {
    const count = pendingTasks.length;
    if (els.taskCountBadge) {
      els.taskCountBadge.textContent = String(count);
    }
    if (els.proactiveTasksSection) {
      els.proactiveTasksSection.hidden = count === 0;
    }
    if (els.stageNotifEmpty) {
      els.stageNotifEmpty.hidden = notificationInbox.length > 0 || count > 0;
    }
    if (!els.stageTaskList) return;

    if (count === 0) {
      els.stageTaskList.replaceChildren();
      requestExpandedHeightUpdate();
      return;
    }

    const fragment = document.createDocumentFragment();
    for (const task of pendingTasks) {
      const item = document.createElement("div");
      const dueTs = task.due_at ?? task.remind_at;
      const isOverdue = Boolean(dueTs && Number(dueTs) * 1000 < Date.now());
      item.className = `task-item${isOverdue ? " is-overdue" : ""}`;
      item.setAttribute("role", "listitem");
      item.dataset.taskId = String(task.id);

      const info = document.createElement("div");
      info.className = "task-item__head";

      const titleEl = document.createElement("strong");
      titleEl.className = "task-item__title";
      titleEl.textContent = task.title || "Tarea pendiente";

      const metaEl = document.createElement("span");
      metaEl.className = "task-item__meta";
      const whenText = formatTaskDue(task.due_at, task.remind_at);
      metaEl.textContent = task.private ? `🔒 ${whenText}` : whenText;

      info.append(titleEl, metaEl);

      const actions = document.createElement("div");
      actions.className = "task-item__actions";

      const doneBtn = document.createElement("button");
      doneBtn.type = "button";
      doneBtn.className = "task-btn task-btn--done";
      doneBtn.dataset.taskAction = "done";
      doneBtn.dataset.taskId = String(task.id);
      doneBtn.title = "Marcar como hecha";
      doneBtn.setAttribute("aria-label", `Completar ${task.title || "tarea"}`);
      doneBtn.textContent = "✓";

      const snoozeBtn = document.createElement("button");
      snoozeBtn.type = "button";
      snoozeBtn.className = "task-btn task-btn--snooze";
      snoozeBtn.dataset.taskAction = "snooze";
      snoozeBtn.dataset.taskId = String(task.id);
      snoozeBtn.dataset.minutes = "10";
      snoozeBtn.title = "Posponer 10 minutos";
      snoozeBtn.setAttribute("aria-label", `Posponer ${task.title || "tarea"} 10 minutos`);
      snoozeBtn.textContent = "💤 10m";

      const deleteBtn = document.createElement("button");
      deleteBtn.type = "button";
      deleteBtn.className = "task-btn task-btn--delete";
      deleteBtn.dataset.taskAction = "delete";
      deleteBtn.dataset.taskId = String(task.id);
      deleteBtn.title = "Eliminar tarea";
      deleteBtn.setAttribute("aria-label", `Eliminar ${task.title || "tarea"}`);
      deleteBtn.textContent = "✕";

      actions.append(doneBtn, snoozeBtn, deleteBtn);
      item.append(info, actions);
      fragment.append(item);
    }

    els.stageTaskList.replaceChildren(fragment);
    requestExpandedHeightUpdate();
  }

  async function fetchPendingTasks(wsUrlOverride, tokenOverride) {
    const cfg = coreHttpConfig(wsUrlOverride, tokenOverride);
    if (!cfg) return pendingTasks;
    try {
      const res = await fetch(
        `${cfg.baseUrl}/v1/users/${encodeURIComponent(proactiveUser)}/tasks?status=pending`,
        { headers: cfg.headers }
      );
      if (!res.ok) {
        console.warn(`[MEKA] GET /v1/users/${proactiveUser}/tasks respondió HTTP ${res.status}`);
        return pendingTasks;
      }
      const data = await res.json();
      pendingTasks = Array.isArray(data?.tasks) ? data.tasks : [];
      renderPendingTasks();
      return pendingTasks;
    } catch (err) {
      reportCoreFetchError(`/v1/users/${proactiveUser}/tasks`, err);
      return pendingTasks;
    }
  }

  async function sendTaskAction(id, action, minutes) {
    if (id == null) return;
    const numId = Number(id);
    const payload = {
      id: numId,
      action,
      ...(minutes ? { minutes: Number(minutes) } : {}),
    };
    logActivity("user.task", `${action}:${numId}`);

    let sentViaWs = false;
    if (core.connected) {
      try {
        core.send({ type: "user.task", data: payload });
        sentViaWs = true;
      } catch {
        sentViaWs = false;
      }
    }

    if (!sentViaWs) {
      const cfg = coreHttpConfig();
      if (cfg) {
        try {
          const res = await fetch(
            `${cfg.baseUrl}/v1/users/${encodeURIComponent(proactiveUser)}/tasks/${encodeURIComponent(numId)}`,
            {
              method: "POST",
              headers: { ...cfg.headers, "Content-Type": "application/json" },
              body: JSON.stringify({
                action,
                ...(minutes ? { minutes: Number(minutes) } : {}),
              }),
            }
          );
          if (!res.ok) {
            console.warn(`[MEKA] POST /v1/users/${proactiveUser}/tasks/${numId} respondió HTTP ${res.status}`);
          }
        } catch (err) {
          reportCoreFetchError(`/v1/users/${proactiveUser}/tasks/${numId}`, err);
        }
      }
      await fetchPendingTasks();
    } else {
      setTimeout(() => {
        fetchPendingTasks();
      }, 180);
    }
  }

  async function triggerProactiveCheck() {
    const cfg = coreHttpConfig();
    if (!cfg) {
      say("Conéctate a MEKA Core para revisar tus pendientes ✨", {
        directToDock: true,
        dockTone: "idle",
        dockBadge: "✨ Pendientes",
        forceExpand: Boolean(pet.autoExpandEvents),
        pulseState: "thinking",
      });
      return null;
    }
    try {
      const res = await fetch(`${cfg.baseUrl}/v1/proactive/check`, {
        method: "POST",
        headers: cfg.headers,
      });
      await fetchPendingTasks();
      const data = res.ok ? await res.json() : null;
      if (data?.nudge?.text) {
        if (!core.connected) {
          showProactiveAlert({
            kind: data.nudge.kind || "nudge",
            taskId: null,
            title: data.nudge.text,
            kicker: "💡 Hanna Proactiva",
            icon: "✨",
            showTaskActions: false,
            skipPulse: true,
          });
          say(data.nudge.text, {
            duration: 7500,
            directToDock: true,
            dockTone: "nudge",
            dockBadge: "💡 Hanna",
            forceExpand: Boolean(pet.autoExpandEvents),
          });
        }
        return data;
      }
      if (notchExpanded && stageView !== "hero") {
        setStageView("hero");
      }
      if (pendingTasks.length > 0) {
        const preview = pendingTasks.slice(0, 3).map((t) => t.title).join(", ");
        const extra = pendingTasks.length > 3 ? ` y ${pendingTasks.length - 3} más` : "";
        say(`Tienes ${pendingTasks.length} pendiente(s): ${preview}${extra}.`, {
          duration: 7000,
          forceExpand: Boolean(pet.autoExpandEvents),
          directToDock: true,
          dockTone: "reminder",
          dockBadge: "📌 Pendientes",
        });
      } else {
        say("No tienes pendientes ni recordatorios próximos ✅", {
          duration: 5000,
          forceExpand: Boolean(pet.autoExpandEvents),
          directToDock: true,
          dockTone: "idle",
          dockBadge: "✅ Al día",
        });
      }
      return data;
    } catch (err) {
      reportCoreFetchError("POST /v1/proactive/check", err);
      say("No pude consultar tus pendientes ahora mismo.", {
        forceExpand: Boolean(pet.autoExpandEvents),
        directToDock: true,
        dockTone: "error",
        dockBadge: "⚠️ Sin conexión",
        pulseState: "error",
      });
      return null;
    }
  }

  // ------------------------------------------------------------------ contrato de eventos con MEKA Core

  const EVENTS = {
    "agent.working": (d) => {
      agentWorking = true;
      if (pet.sleeping) wake({ quiet: true });
      setBase("working", { interrupt: true });
      if (!focusActive) {
        say(d.task ? `Trabajando en: ${d.task} 📂` : line("working"), {
          directToDock: true,
          dockTone: "working",
          dockBadge: "⚙️ Trabajando",
        });
      }
    },
    "agent.done": (d) => {
      agentWorking = false;
      if (!pet.sleeping) base = "idle";
      if (!focusActive) {
        play("celebrate", d.summary || line("celebrate"), {
          directToDock: true,
          dockTone: "reply",
          dockBadge: "✅ Completado",
        });
      } else {
        show("idle");
      }
    },
    "agent.error": (d) => {
      agentWorking = false;
      if (!pet.sleeping) base = "idle";
      play("error");
      say(d.message || line("error"), {
        forceExpand: Boolean(pet.autoExpandEvents),
        directToDock: true,
        dockTone: "error",
        dockBadge: "⚠️ Error",
        pulseState: "error",
      });
    },
    "agent.confirm": (d) => {
      const confirmId = d.id || `confirm-${Date.now()}`;
      // Calcular duración precisa a partir de expires_at o timeout del Core
      let durationMs = 120_000;
      if (d.expires_at) {
        const remainingSeconds = d.expires_at - (Date.now() / 1000);
        durationMs = Math.max(2000, Math.round(remainingSeconds * 1000));
      } else if (d.timeout) {
        durationMs = Math.max(2000, d.timeout * 1000);
      }
      play(
        "thinking",
        `¿Autorizas ${d.action || "ejecutar esta acción"}?`,
        {
          confirmId,
          duration: durationMs,
          pulseState: "surprise",
          pulseText: `🔐 Autorizar: ${d.action || "acción"}`,
        }
      );
    },
    "agent.confirmed": (d) => {
      // Cierra el diálogo de confirmación si se resolvió en otro cliente (ej. Telegram), API o timeout
      if (pendingConfirmId && (!d.id || pendingConfirmId === d.id)) {
        const hadQueued = pendingDockQueue.length > 0;
        clearTimeout(bubbleTimer);
        pendingConfirmId = null;
        if (els.confirmBar) els.confirmBar.hidden = true;
        if (els.bubbleTag) els.bubbleTag.hidden = true;
        if (els.agentReplyDock) delete els.agentReplyDock.dataset.confirmPending;
        ensureBubbleAlwaysHidden();
        if (d.approved) {
          play("celebrate", `Autorizado por ${d.by || "usuario"} ✨`, {
            directToDock: true,
            dockTone: "reply",
            dockBadge: "✅ Autorizado",
          });
        } else {
          play("idle", d.by === "timeout" ? "Tiempo de espera de autorización agotado." : "Acción cancelada.", {
            directToDock: true,
            dockTone: "idle",
            dockBadge: "✕ Cancelado",
          });
        }
        if (hadQueued) {
          const seqAfterResolve = dockUpdateSeq;
          setTimeout(() => {
            if (!pendingConfirmId && dockUpdateSeq === seqAfterResolve) {
              flushPendingDockQueue();
            }
          }, 1600);
        }
      }
    },
    message: (d) => {
      const st = normalizeEmotion(d.emotion, d.text) || "happy";
      if (st === "error") {
        play("error");
        say(d.text || line("error"), {
          forceExpand: Boolean(pet.autoExpandEvents),
          directToDock: true,
          dockTone: "error",
          dockBadge: "⚠️ Error",
          pulseState: "error",
        });
      } else {
        play(st, d.text, {
          directToDock: true,
          dockTone: "reply",
          dockBadge: d.private ? "🔒 Respuesta" : "💬 Respuesta",
          pulseState: st,
        });
      }
    },
    emotion: (d) => {
      const state = normalizeEmotion(d.emotion, d.text);
      if (state) play(state);
    },
    "budget.low": () => play("sad", line("broke"), {
      directToDock: true,
      dockTone: "error",
      dockBadge: "💸 Presupuesto",
    }),
    "system.media": (d) => applySystemMedia(d),
    "system.battery": (d) => updateBattery(d),
    "system.notification": (d) => onNotification(d),
    "system.notification_removed": (d) => onNotificationRemoved(d),
    "focus.started": (d) => handleFocusStarted(d),
    "focus.ended": (d) => handleFocusEnded(d),
    "reminder.due": (d) => {
      const reminderText = d.text || d.title || "Recordatorio pendiente";
      showProactiveAlert({
        kind: "reminder",
        taskId: d.id,
        title: d.title || d.text || "Recordatorio pendiente",
        kicker: "⏰ Recordatorio de Hanna",
        icon: "⏰",
        showTaskActions: Boolean(d.id),
        mood: "surprise",
        skipPulse: true,
      });
      say(reminderText, {
        duration: 7000,
        forceExpand: Boolean(pet.autoExpandEvents),
        directToDock: true,
        dockTone: "reminder",
        dockBadge: d.private ? "🔒 Recordatorio" : "⏰ Recordatorio",
        pulseState: "surprise",
        pulseText: d.title || reminderText,
      });
      fetchPendingTasks();
    },
    nudge: (d) => {
      if (!focusActive) {
        const isWelcome = d.kind === "welcome";
        const nudgeMood = isWelcome ? "greet" : "happy";
        showProactiveAlert({
          kind: d.kind || "nudge",
          taskId: null,
          title: d.text || "Tienes pendientes por revisar",
          kicker: isWelcome ? "👋 Mientras no estabas" : "💡 Hanna Proactiva",
          icon: isWelcome ? "👋" : "✨",
          showTaskActions: false,
          mood: nudgeMood,
          skipPulse: Boolean(d.text),
        });
        if (d.text) {
          say(d.text, {
            duration: 7500,
            forceExpand: Boolean(pet.autoExpandEvents),
            directToDock: true,
            dockTone: "nudge",
            dockBadge: isWelcome ? "👋 Mientras no estabas" : "💡 Hanna",
            pulseState: nudgeMood,
          });
        }
      }
      fetchPendingTasks();
    },
    "task.changed": (d) => {
      const isSameAlert =
        activeProactiveAlert &&
        activeProactiveAlert.taskId != null &&
        Number(activeProactiveAlert.taskId) === Number(d.id);
      if (
        isSameAlert &&
        (d.status === "done" ||
          d.action === "delete" ||
          d.action === "deleted" ||
          d.action === "snooze" ||
          d.action === "snoozed")
      ) {
        hideProactiveAlert();
      }
      fetchPendingTasks();
    },
  };

  function handleEvent(event) {
    const handler = event && EVENTS[event.type];
    if (!handler) {
      console.warn("Evento desconocido de MEKA Core:", event);
      return;
    }
    const detail =
      event.data?.task ||
      event.data?.summary ||
      event.data?.message ||
      event.data?.action ||
      event.data?.text ||
      event.data?.emotion ||
      (event.data?.app ? `${event.data.app}: ${event.data.title || event.data.body || ""}` : "") ||
      "";
    logActivity(event.type, detail);
    handler(event.data || {});
  }

  // ------------------------------------------------------------------ Eventos nativos locales de Windows (pet/desktop -> window.MEKA.emitNativeEvent)

  const NATIVE_WINDOWS_EVENTS = {
    "win.idle": (d = {}) => {
      lastNativeIdleAt = Date.now();
      clearTimeout(localYawnTimer);
      localYawnTimer = null;
      isLocalYawning = false;

      const phase = String(d.phase || "").toLowerCase();
      if (phase === "yawn") {
        if (!pet.sleeping && !agentWorking && !pendingConfirmId && !activeMedia?.playing) {
          clearTimeout(transientTimer);
          transientTimer = null;
          show("yawn");
          say(line("yawn"), {
            suppressAutoExpand: true,
            pulseState: "yawn",
            pulseText: "Bostezando… 🥱",
          });
        }
        return;
      }

      if (phase === "sleeping" || (d.idle === true && phase !== "active")) {
        if (!agentWorking && !pendingConfirmId && !activeMedia?.playing) {
          enterAutoSleep();
        }
        return;
      }

      if (phase === "active" || d.idle === false) {
        scheduleInactivityTimer();
        if (isAutoSleeping || current === "yawn") {
          if (pet.sleeping) {
            wake();
          } else {
            const restoredBase = agentWorking
              ? "working"
              : (activeWindowsContext === "gaming"
                ? "gaming"
                : (activeWindowsContext === "coding" || activeWindowsContext === "meeting" ? "focus" : "idle"));
            setBase(restoredBase, { interrupt: true });
            show(base);
          }
        }
      }
    },

    "win.power": (d = {}) => {
      const hasPlugged = typeof d.plugged === "boolean" || typeof d.charging === "boolean";
      const plugged = hasPlugged ? Boolean(d.plugged ?? d.charging) : lastPowerPlugged;
      // Si lastPowerPlugged === null (primer estado recibido), guardar sin disparar animación engañosa
      const becamePlugged = hasPlugged && lastPowerPlugged === false && plugged === true;
      const isLowOrSaver = Boolean(d.low || d.saver);
      const becameLowOrSaver = lastPowerPlugged !== null && !plugged && isLowOrSaver && !lastPowerLowOrSaver;

      if (typeof d.percent === "number" && Number.isFinite(d.percent)) {
        updateBattery({ percent: d.percent, charging: Boolean(plugged) });
      }

      lastPowerPlugged = plugged;
      lastPowerLowOrSaver = isLowOrSaver;

      if (becamePlugged) {
        play("charging", "⚡ Cargador conectado", {
          suppressAutoExpand: true,
          pulseState: "charging",
          pulseText: "⚡ Cargador conectado",
          duration: 4200,
        });
        return;
      }

      if (becameLowOrSaver) {
        const msg = d.saver ? "🔋 Ahorro de batería activo" : "🪫 Batería baja";
        if (!pet.sleeping) {
          play("dizzy", msg, {
            suppressAutoExpand: true,
            pulseState: "dizzy",
            pulseText: msg,
            brandColor: "#f59e0b",
            brandColor2: "#fbbf24",
            duration: 4200,
          });
        } else {
          triggerIslandSubtlePulse("dizzy", msg, {
            brandColor: "#f59e0b",
            brandColor2: "#fbbf24",
          });
        }
      }
    },

    "win.session": (d = {}) => {
      const st = String(d.state || d.action || "").toLowerCase();
      if (st === "locked" || st === "suspend") {
        lastNativeIdleAt = Date.now();
        enterAutoSleep();
        return;
      }
      if (st === "unlocked" || st === "resume") {
        lastNativeIdleAt = Date.now();
        scheduleInactivityTimer();
        // Respetar el reposo manual si el usuario lo activó explícitamente antes del bloqueo
        if (pet.sleeping && !isAutoSleeping) {
          return;
        }
        isAutoSleeping = false;
        pet.sleeping = false;
        setBase(agentWorking ? "working" : "idle", { interrupt: true });
        play("greet", "¡Hola de nuevo! ✨", {
          suppressAutoExpand: true,
          pulseState: "greet",
          pulseText: "¡Hola de nuevo! ✨",
          duration: 4200,
        });
        triggerTempBodyMotion("peek", 1800);
        save();
      }
    },

    "win.context": (d = {}) => {
      const mode = String(d.mode || "normal").toLowerCase();
      activeWindowsContext = mode;
      if (pet.sleeping || isAutoSleeping || agentWorking || pendingConfirmId || activeMedia?.playing) {
        return;
      }

      if (mode === "gaming") {
        clearTimeout(transientTimer);
        transientTimer = null;
        setBase("gaming", { interrupt: true });
        show("gaming");
        if (!notchExpanded) {
          triggerIslandSubtlePulse("gaming", d.app ? `🎮 ${d.app}` : "Modo Gaming 🎮");
        }
        return;
      }

      if (mode === "coding") {
        clearTimeout(transientTimer);
        transientTimer = null;
        setBase("focus", { interrupt: true });
        show("focus");
        if (!notchExpanded) {
          triggerIslandSubtlePulse("focus", d.app ? `🎯 ${d.app}` : "Enfoque activo 🎯");
        }
        return;
      }

      if (mode === "meeting") {
        clearTimeout(transientTimer);
        transientTimer = null;
        setBase("focus", { interrupt: true });
        show("focus");
        triggerTempBodyMotion("shush", 2400);
        if (!notchExpanded) {
          triggerIslandSubtlePulse("focus", d.app ? `🤫 ${d.app}` : "🤫 En reunión");
        }
        return;
      }

      if (base === "gaming" || base === "focus" || current === "gaming" || current === "focus") {
        setBase(agentWorking ? "working" : "idle", { interrupt: true });
        show(base);
      }
    },

    "win.device": (d = {}) => {
      const st = String(d.state || d.action || "").toLowerCase();
      const kind = String(d.kind || d.type || "usb").toLowerCase();
      if (st === "connected") {
        const label = kind === "audio" ? "🎧 Dispositivo conectado" : "🔌 USB conectado";
        play("curious", label, {
          suppressAutoExpand: true,
          pulseState: "curious",
          pulseText: label,
          duration: 4200,
        });
        return;
      }
      if (st === "disconnected") {
        const label = kind === "audio" ? "🎧 Dispositivo desconectado" : "🔌 USB desconectado";
        play("sigh", label, {
          suppressAutoExpand: true,
          pulseState: "sigh",
          pulseText: label,
          duration: 3600,
        });
      }
    },

    "win.screenshot": () => {
      triggerTempBodyMotion("camera", 1800);
      spawnParticles("📸", 3);
      spawnMiniParticles("📸", 2);
      try {
        els.stage?.animate(
          [{ filter: "brightness(1)" }, { filter: "brightness(1.25)" }, { filter: "brightness(1)" }],
          { duration: 460, easing: "ease-out" }
        );
      } catch (_) {}
      say("📸 Captura detectada", {
        suppressAutoExpand: true,
        pulseState: "surprise",
        pulseText: "📸 Captura detectada",
        brandColor: "#e2e8f0",
      });
    },

    "win.network": (d = {}) => {
      if (typeof d.online !== "boolean") return;
      const isOnline = d.online;
      const prevOnline = lastNetworkOnline;
      lastNetworkOnline = isOnline;

      if (!isOnline) {
        play("dizzy", "📡 Sin conexión", {
          suppressAutoExpand: true,
          pulseState: "dizzy",
          pulseText: "📡 Sin conexión",
          brandColor: "#f59e0b",
          duration: 4500,
        });
        return;
      }

      if (prevOnline !== true) {
        play("happy", "🌐 Conexión restaurada", {
          suppressAutoExpand: true,
          pulseState: "happy",
          pulseText: "🌐 Conexión restaurada",
          brandColor: "#30d158",
          brandColor2: "#4ade80",
          duration: 4200,
        });
      }
    },

    "win.volume": (d = {}) => {
      const hasPercent = typeof d.percent === "number" && Number.isFinite(d.percent);
      const pct = hasPercent ? Math.max(0, Math.min(100, Math.round(d.percent))) : lastVolumePercent;
      const hasMuted = typeof d.muted === "boolean";
      const muted = hasMuted ? d.muted : Boolean(lastVolumeMuted);

      const prevPercent = lastVolumePercent;
      const prevMuted = lastVolumeMuted;
      lastVolumePercent = pct;
      lastVolumeMuted = muted;

      if (muted === true) {
        triggerTempBodyMotion("shush", 1800);
        if (!notchExpanded) {
          triggerIslandSubtlePulse(current || "idle", "🔇 Silenciado", {
            brandColor: "#94a3b8",
            brandColor2: "#64748b",
          });
        } else if (!activeMedia?.playing && !agentWorking && !pendingConfirmId) {
          updateAgentDock("🔇 Silenciado", {
            tone: "idle",
            badge: "🔊 Audio",
            animate: "update",
          });
        }
        return;
      }

      if (hasPercent && (pct !== prevPercent || prevMuted === true)) {
        const volText = `🔊 Volumen ${pct}%`;
        if (!notchExpanded) {
          triggerIslandSubtlePulse(current || "idle", volText);
        } else if (!activeMedia?.playing && !agentWorking && !pendingConfirmId) {
          updateAgentDock(volText, {
            tone: "idle",
            badge: "🔊 Audio",
            animate: "update",
          });
        }
      }
    },
  };

  function emitNativeEvent(event) {
    if (!event || typeof event !== "object") return false;
    if (!pet.winEventsEnabled) return false;
    const type = String(event.type || "").trim();
    const handler = type && Object.hasOwn(NATIVE_WINDOWS_EVENTS, type)
      ? NATIVE_WINDOWS_EVENTS[type]
      : null;
    if (!handler) {
      console.warn("[MEKA] Evento nativo de Windows desconocido:", event);
      return false;
    }
    const data = event.data && typeof event.data === "object" ? event.data : event;
    const detail =
      data.phase ||
      data.mode ||
      data.state ||
      data.source ||
      (typeof data.online === "boolean" ? (data.online ? "online" : "offline") : "") ||
      (typeof data.percent === "number" ? `${Math.round(data.percent)}%` : "");
    logActivity(type, String(detail || ""));
    handler(data);
    return true;
  }

  // ------------------------------------------------------------------ conexión WebSocket + REST

  function setCoreStatus(text, connected = false) {
    core.offline = !connected && text !== "conectando…";
    const el = $("coreStatus");
    if (el) el.textContent = text;
    if (els.coreBadge) els.coreBadge.dataset.connected = String(connected);
    if (els.hudCoreText) els.hudCoreText.textContent = connected ? "Core: Conectado" : "Core desconectado";
    if (els.hudCoreDot) {
      els.hudCoreDot.style.background = connected ? "#30d158" : "#ff453a";
      els.hudCoreDot.style.boxShadow = connected ? "0 0 6px #30d158" : "0 0 6px #ff453a";
    }
    updateStageBadges();
  }

  function buildWsUrl(rawUrl, token) {
    if (!token) return rawUrl;
    try {
      const u = new URL(rawUrl);
      u.searchParams.set("token", token);
      return u.toString();
    } catch {
      return rawUrl;
    }
  }

  async function fetchPendingConfirmations(rawUrl, token = "") {
    try {
      const u = new URL(rawUrl);
      const httpProto = u.protocol === "wss:" ? "https:" : "http:";
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await fetch(`${httpProto}//${u.host}/v1/confirmations`, { headers });
      if (!res.ok) {
        console.warn(`[MEKA] GET /v1/confirmations respondió HTTP ${res.status}`);
        return;
      }
      const data = await res.json();
      const list = Array.isArray(data.pending) ? data.pending : [];
      if (list.length > 0) {
        const oldest = list[0];
        logActivity("confirm.pending", `${oldest.id}: ${oldest.action}`);
        handleEvent({ type: "agent.confirm", data: oldest });
      }
    } catch (err) {
      reportCoreFetchError("GET /v1/confirmations", err);
    }
  }

  async function inspectCoreHealthAndContract(wsUrl, token = "") {
    if (!els.coreHealthInfo) return;
    try {
      const u = new URL(wsUrl);
      const httpProto = u.protocol === "wss:" ? "https:" : "http:";
      const headers = token ? { Authorization: `Bearer ${token}` } : {};

      // 1. Consultar estado del núcleo (/v1/health)
      const healthRes = await fetch(`${httpProto}//${u.host}/v1/health`, { headers });
      if (!healthRes.ok) {
        console.warn(`[MEKA] GET /v1/health respondió HTTP ${healthRes.status}`);
        return;
      }
      const healthData = await healthRes.json();

      // 2. Consultar contrato publicado (/v1/contract) y verificar compatibilidad
      let contractVersion = healthData.contract || "1.0";
      try {
        const contractRes = await fetch(`${httpProto}//${u.host}/v1/contract`);
        if (contractRes.ok) {
          const contractData = await contractRes.json();
          if (contractData.version) contractVersion = contractData.version;
        } else {
          console.warn(`[MEKA] GET /v1/contract respondió HTTP ${contractRes.status}`);
        }
      } catch (err) {
        console.warn("[MEKA] Error al consultar /v1/contract:", err);
      }

      const major = String(contractVersion).split(".")[0];
      if (major !== "1") {
        els.coreHealthInfo.textContent = `⚠️ Contrato incompatible: Core v${contractVersion} (se esperaba 1.x). Actualiza MEKA.`;
        els.coreHealthInfo.hidden = false;
        logActivity("contract.warn", `Versión mayor incompatible: ${contractVersion}`);
        return;
      }

      // Sincronizar personaje activo de MEKA Core con los avatares disponibles
      const activePersona = healthData.persona;
      const personaSkinMap = { dva: "hana", hana: "hana", "2b": "2b", kiriko: "kiriko", marin: "marin", yotsuba: "yotsuba" };
      if (activePersona && personaSkinMap[activePersona] && CATALOG.skins[personaSkinMap[activePersona]]) {
        const candidate = personaSkinMap[activePersona];
        if (!params.get("skin") && pet.skin !== candidate && !localStorage.getItem(STORAGE_KEY)) {
          setSkin(candidate);
        }
      }

      const brainSummary = typeof healthData.brain === "object"
        ? (healthData.brain.model || "Local")
        : (healthData.brain || "Local");

      els.coreHealthInfo.textContent = `Core v${healthData.version} · Contrato v${contractVersion} · ${healthData.persona || "MEKA"} · ${brainSummary}`;
      els.coreHealthInfo.hidden = false;
      logActivity("core.ready", `Contrato v${contractVersion} verificado`);
    } catch (err) {
      els.coreHealthInfo.hidden = true;
      reportCoreFetchError("GET /v1/health", err);
    }
  }

  let activeTtsAudio = null;
  let activeTtsObjectUrl = null;

  async function playAudioClip(audioId) {
    if (!audioId) return;
    try {
      const ep = coreHttpEndpoint(`/v1/audio/${encodeURIComponent(String(audioId))}`);
      const res = await fetch(ep.url, { headers: ep.headers });
      if (!res.ok) return;
      const blob = await res.blob();
      if (activeTtsAudio) {
        try { activeTtsAudio.pause(); } catch (_) {}
      }
      if (activeTtsObjectUrl) {
        URL.revokeObjectURL(activeTtsObjectUrl);
        activeTtsObjectUrl = null;
      }
      const clipUrl = URL.createObjectURL(blob);
      activeTtsObjectUrl = clipUrl;
      const audio = new Audio(clipUrl);
      activeTtsAudio = audio;
      const cleanup = () => {
        if (activeTtsObjectUrl === clipUrl) {
          URL.revokeObjectURL(clipUrl);
          activeTtsObjectUrl = null;
        }
      };
      audio.addEventListener("ended", cleanup, { once: true });
      audio.addEventListener("error", cleanup, { once: true });
      await audio.play().catch((err) => {
        console.warn("[MEKA] Audio autoplay/playback bloqueado:", err);
      });
    } catch (err) {
      console.warn("[MEKA] Audio playback opcional falló:", err);
    }
  }

  async function fetchCoreDiagnosticsSummary(wsUrlOverride, tokenOverride) {
    if (!els.coreRunsSummary) return;
    try {
      const runsEp = coreHttpEndpoint("/v1/runs?days=7&limit=5", wsUrlOverride, tokenOverride);
      const proactiveEp = coreHttpEndpoint("/v1/proactive", wsUrlOverride, tokenOverride);
      const [runsRes, proRes] = await Promise.allSettled([
        fetch(runsEp.url, { headers: runsEp.headers }),
        fetch(proactiveEp.url, { headers: proactiveEp.headers }),
      ]);

      const parts = [];
      if (runsRes.status === "fulfilled" && runsRes.value.ok) {
        const runsData = await runsRes.value.json();
        const summary = runsData.summary || {};
        const totalRuns = Number(summary.runs ?? runsData.runs?.length ?? 0);
        const totalCost = Number(summary.cost_usd ?? 0);
        parts.push(`Últimos 7d: ${totalRuns} ejec.${totalCost > 0 ? ` ($${totalCost.toFixed(4)})` : ""}`);
      }
      if (proRes.status === "fulfilled" && proRes.value.ok) {
        const proData = await proRes.value.json();
        const statusTxt = proData.enabled === false
          ? "Pausado"
          : (proData.at_desk ? "Activo · en escritorio" : "Activo");
        parts.push(`Proactivo: ${statusTxt}`);
      }

      if (parts.length > 0) {
        els.coreRunsSummary.textContent = parts.join(" · ");
        els.coreRunsSummary.hidden = false;
      } else {
        els.coreRunsSummary.hidden = true;
      }
    } catch (err) {
      els.coreRunsSummary.hidden = true;
      reportCoreFetchError("/v1/runs /v1/proactive", err);
    }
  }

  async function resetCoreSession() {
    if (!core.connected) {
      updateAgentDock("Conecta MEKA Core primero para reiniciar la sesión.", {
        tone: "error",
        badge: "⚠️ Sin conexión",
        animate: "update",
      });
      return;
    }
    try {
      const ep = coreHttpEndpoint("/v1/sessions/ws%3Apet/reset");
      const res = await fetch(ep.url, { method: "POST", headers: ep.headers });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      logActivity("session.reset", "ws:pet reiniciada");
      updateAgentDock("Memoria de esta sesión reiniciada.", {
        tone: "idle",
        badge: "🧹 Sesión limpia",
        animate: "update",
      });
      if (els.coreRunsSummary) {
        els.coreRunsSummary.textContent = "Sesión ws:pet reiniciada correctamente.";
        els.coreRunsSummary.hidden = false;
      }
      setTimeout(() => fetchCoreDiagnosticsSummary(), 600);
    } catch (err) {
      console.warn("[MEKA] Error en POST /v1/sessions/ws:pet/reset:", err);
      updateAgentDock("No pude reiniciar la sesión en MEKA Core.", {
        tone: "error",
        badge: "⚠️ Error",
        animate: "update",
      });
    }
  }

  async function createQuickTask(rawTitle) {
    const title = String(rawTitle || "").trim();
    if (!title) return false;
    try {
      const ep = coreHttpEndpoint(`/v1/users/${encodeURIComponent(proactiveUser)}/tasks`);
      const res = await fetch(ep.url, {
        method: "POST",
        headers: {
          ...ep.headers,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title,
          private: Boolean(pet.privateMode),
          source: "pet",
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      logActivity("task.create", title);
      await fetchPendingTasks();
      updateAgentDock(`Recordatorio guardado: ${title}`, {
        tone: "reminder",
        badge: pet.privateMode ? "🔒 Tarea" : "📌 Tarea",
        animate: "update",
      });
      return true;
    } catch (err) {
      reportCoreFetchError(`POST /v1/users/${proactiveUser}/tasks`, err);
      say("No pude guardar la tarea en MEKA Core.", {
        forceExpand: Boolean(pet.autoExpandEvents),
        directToDock: true,
        dockTone: "error",
        dockBadge: "⚠️ Tarea",
        pulseState: "error",
      });
      return false;
    }
  }

  async function fetchSystemSnapshot(wsUrl, token = "", { silent = false } = {}) {
    try {
      const u = new URL(wsUrl);
      const httpProto = u.protocol === "wss:" ? "https:" : "http:";
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await fetch(`${httpProto}//${u.host}/v1/system`, { headers, cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        if (data && typeof data === "object") {
          if (data.media && (data.media.title || data.media.playing)) {
            const nextPlaying = Boolean(data.media.playing);
            const nextTitle = data.media.title || "Sin título";
            const nextArtist = data.media.artist || "";
            const nextArt = data.media.artwork || null;
            const mediaChanged = !activeMedia
              ? true
              : (
                  nextPlaying !== Boolean(activeMedia.playing) ||
                  nextTitle !== activeMedia.title ||
                  nextArtist !== activeMedia.artist ||
                  (nextArt !== null && nextArt !== activeMedia.artwork)
                );
            if (mediaChanged || !silent) {
              updateMedia(data.media);
            } else if (typeof data.media.position === "number" && activeMedia) {
              if (Math.abs((activeMedia.position || 0) - data.media.position) > 2.5) {
                activeMedia.position = data.media.position;
                if (typeof data.media.duration === "number") activeMedia.duration = data.media.duration;
                renderMediaProgress();
              }
            }
          } else if (activeMedia !== null || !silent) {
            updateMedia(null);
          }
          if (data.battery) updateBattery(data.battery);
        }
      } else {
        console.warn(`[MEKA] GET /v1/system respondió HTTP ${res.status}`);
      }
    } catch (err) {
      reportCoreFetchError("GET /v1/system", err);
    }

    try {
      const u = new URL(wsUrl);
      const httpProto = u.protocol === "wss:" ? "https:" : "http:";
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const notifRes = await fetch(`${httpProto}//${u.host}/v1/system/notifications`, { headers, cache: "no-store" });
      if (notifRes.ok) {
        const notifData = await notifRes.json();
        const list = Array.isArray(notifData.notifications) ? notifData.notifications : [];
        if (!initialNotificationsLoaded) {
          initialNotificationsLoaded = true;
          notificationInbox.length = 0;
          for (const item of list) {
            if (item?.id != null) seenNotificationIds.add(Number(item.id));
            notificationInbox.push(item);
          }
          renderNotifBrief();
          renderNotifInbox();
        } else {
          const serverIds = new Set(list.map((it) => Number(it?.id)).filter(Number.isFinite));
          for (const item of [...list].reverse()) {
            if (!item || item.id == null) continue;
            const nid = Number(item.id);
            if (!seenNotificationIds.has(nid)) {
              seenNotificationIds.add(nid);
              onNotification(item);
            }
          }
          const existingIds = notificationInbox.map((n) => Number(n.id));
          for (const oldId of existingIds) {
            if (!serverIds.has(oldId)) {
              onNotificationRemoved({ id: oldId });
            }
          }
        }
      } else {
        console.warn(`[MEKA] GET /v1/system/notifications respondió HTTP ${notifRes.status}`);
      }
    } catch (err) {
      reportCoreFetchError("GET /v1/system/notifications", err);
    }
  }

  function connectCore(rawUrl, token = "") {
    clearTimeout(core.timer);
    clearInterval(systemSyncTimer);
    systemSyncTimer = null;
    if (core.ws) {
      core.ws.onclose = null;
      core.ws.close();
    }
    core.url = rawUrl || DEFAULT_CORE_URL;
    core.token = token || "";
    const url = buildWsUrl(core.url, core.token);
    setCoreStatus("conectando…", false);
    let ws;
    try {
      ws = new WebSocket(url);
    } catch {
      core.offline = true;
      setCoreStatus("URL no válida", false);
      return;
    }
    core.ws = ws;
    ws.onopen = () => {
      core.connected = true;
      core.offline = false;
      core.retry = 1000;
      setCoreStatus("conectado", true);
      logActivity("ws.open", rawUrl);
      core.send({ type: "client.hello", data: { client: "pet", skin: pet.skin } });
      inspectCoreHealthAndContract(rawUrl, token);
      fetchCoreDiagnosticsSummary(rawUrl, token);
      fetchPendingConfirmations(rawUrl, token);
      fetchSystemSnapshot(rawUrl, token, { silent: false });
      fetchFocusStatus(rawUrl, token);
      fetchPendingTasks(rawUrl, token);
      clearInterval(systemSyncTimer);
      systemSyncTimer = setInterval(() => {
        if (core.connected) {
          fetchSystemSnapshot(core.url, core.token, { silent: true });
        }
      }, 3000);
    };
    ws.onmessage = (message) => {
      try {
        handleEvent(JSON.parse(message.data));
      } catch {
        console.warn("Mensaje no válido de MEKA Core:", message.data);
      }
    };
    ws.onclose = () => {
      core.connected = false;
      core.offline = true;
      clearInterval(systemSyncTimer);
      systemSyncTimer = null;
      setCoreStatus(`desconectado (reintento en ${core.retry / 1000} s)`, false);
      core.timer = setTimeout(() => connectCore(rawUrl, token), core.retry);
      core.retry = Math.min(core.retry * 2, 30_000);
    };
  }

  // ------------------------------------------------------------------ renderizado del Drawer de personajes

  function renderSkinCards() {
    if (!els.skinCards) return;
    els.skinCards.replaceChildren();
    for (const [id, sk] of Object.entries(CATALOG.skins)) {
      const card = document.createElement("button");
      card.type = "button";
      card.className = `skin-card${id === pet.skin ? " is-active" : ""}`;
      card.setAttribute("role", "radio");
      card.setAttribute("aria-checked", String(id === pet.skin));

      const thumb = document.createElement("img");
      thumb.className = "skin-card__thumb";
      thumb.src = sk.sprites.idle;
      thumb.alt = "";

      const info = document.createElement("span");
      info.className = "skin-card__info";

      const name = document.createElement("strong");
      name.className = "skin-card__name";
      name.textContent = `${sk.name} ${id === pet.skin ? "✓" : ""}`.trim();

      const meta = document.createElement("small");
      meta.className = "skin-card__meta";
      meta.textContent = sk.description;

      info.append(name, meta);
      card.append(thumb, info);
      card.addEventListener("click", () => setSkin(id));
      els.skinCards.append(card);
    }
  }

  function setupControls() {
    applyTheme(pet.theme);
    setGlassMode(pet.glass, { persist: false });
    setPrivateMode(pet.privateMode, { persist: false });
    setAutoExpandMode(pet.autoExpandEvents, { persist: false });
    setWinEventsEnabled(pet.winEventsEnabled, { persist: false });
    syncAutoStartUI();
    updateStageBadges();

    els.themeToggle?.addEventListener("click", () => {
      applyTheme(pet.theme === "dark" ? "light" : "dark");
      save(pet);
    });

    els.settingsCloseBtn?.addEventListener("click", (event) => {
      event.stopPropagation();
      setSettingsCardOpen(false);
    });
    els.privateToggleBtn?.addEventListener("click", (event) => {
      event.stopPropagation();
      setPrivateMode(!pet.privateMode);
    });
    els.autoExpandToggleBtn?.addEventListener("click", (event) => {
      event.stopPropagation();
      setAutoExpandMode(!pet.autoExpandEvents);
    });
    els.winEventsToggleBtn?.addEventListener("click", (event) => {
      event.stopPropagation();
      setWinEventsEnabled(!pet.winEventsEnabled);
    });
    (els.autoStartToggleBtn || $("autoStartToggleBtn"))?.addEventListener("click", (event) => {
      event.stopPropagation();
      toggleAutoStart();
    });
    els.sleepToggleBtn?.addEventListener("click", (event) => {
      event.stopPropagation();
      if (pet.sleeping || isAutoSleeping) wake();
      else sleep();
    });
    els.settingsProactiveBtn?.addEventListener("click", (event) => {
      event.stopPropagation();
      setStageView("hero");
      triggerProactiveCheck();
    });
    els.settingsCenterBtn?.addEventListener("click", (event) => {
      event.stopPropagation();
      centerNotch();
    });
    els.settingsDodgeBtn?.addEventListener("click", (event) => {
      event.stopPropagation();
      toggleDodge();
    });
    els.settingsScreenshotBtn?.addEventListener("click", (event) => {
      event.stopPropagation();
      setStageView("hero");
      hideTemporarilyForScreenshot(10);
    });
    els.closeAppBtn?.addEventListener("click", closeMekaApplication);
    els.topCloseAppBtn?.addEventListener("click", closeMekaApplication);
    (els.heroMoodBar || $("heroMoodBar"))?.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-mood]");
      if (!btn) return;
      event.stopPropagation();
      const mood = btn.dataset.mood;
      if (!mood) return;
      if (mood === "sleeping") {
        if (pet.sleeping || isAutoSleeping) wake();
        else sleep();
        return;
      }
      if (pet.sleeping || isAutoSleeping) wake({ quiet: true });
      const safeMood = validState(mood) || "happy";
      play(safeMood, line(safeMood), { suppressAutoExpand: true });
    });
    els.coreResetSessionBtn?.addEventListener("click", (event) => {
      event.stopPropagation();
      resetCoreSession();
    });
    els.taskQuickForm?.addEventListener("submit", async (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (!els.taskQuickInput) return;
      const ok = await createQuickTask(els.taskQuickInput.value);
      if (ok) {
        els.taskQuickInput.value = "";
      }
    });

    const buttons = $("eventButtons");
    if (buttons) {
      for (const [label, event] of SAMPLE_EVENTS) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = label;
        button.addEventListener("click", () => handleEvent(structuredClone(event)));
        buttons.append(button);
      }
    }

    renderSkinCards();
    logActivity("ready", `Avatar activo: ${skin().name}`);

    $("coreForm")?.addEventListener("submit", (event) => {
      event.preventDefault();
      connectCore($("coreUrl").value.trim(), els.coreToken?.value.trim() || "");
    });
    els.clearLog?.addEventListener("click", () => {
      els.eventLog?.replaceChildren();
    });

    els.mediaPrev?.addEventListener("click", (event) => {
      event.stopPropagation();
      sendMediaAction("previous");
    });
    els.mediaPlayPause?.addEventListener("click", (event) => {
      event.stopPropagation();
      sendMediaAction("play_pause");
    });
    els.mediaNext?.addEventListener("click", (event) => {
      event.stopPropagation();
      sendMediaAction("next");
    });
    els.mediaLikeBtn?.addEventListener("click", (event) => {
      event.stopPropagation();
      const next = els.mediaLikeBtn.getAttribute("aria-pressed") !== "true";
      els.mediaLikeBtn.setAttribute("aria-pressed", String(next));
      els.mediaLikeBtn.classList.toggle("is-active", next);
      if (next) {
        spawnParticles("💜", 5);
      }
    });
    els.mediaShuffleBtn?.addEventListener("click", (event) => {
      event.stopPropagation();
      const next = els.mediaShuffleBtn.getAttribute("aria-pressed") !== "true";
      els.mediaShuffleBtn.setAttribute("aria-pressed", String(next));
      els.mediaShuffleBtn.classList.toggle("is-active", next);
    });
    els.mediaOutputBtn?.addEventListener("click", (event) => {
      event.stopPropagation();
      if (!notchExpanded) {
        setNotchExpanded(true, { view: "media", silent: true });
      } else {
        setStageView("media");
      }
      els.mediaOutputBtn.classList.add("is-active");
      setTimeout(() => els.mediaOutputBtn?.classList.remove("is-active"), 550);
      els.mediaPlayPause?.focus();
    });

    els.proactiveDoneBtn?.addEventListener("click", (event) => {
      event.stopPropagation();
      const taskId = activeProactiveAlert?.taskId;
      if (taskId != null) {
        sendTaskAction(taskId, "done");
      }
      hideProactiveAlert();
    });
    els.proactiveSnoozeBtn?.addEventListener("click", (event) => {
      event.stopPropagation();
      const taskId = activeProactiveAlert?.taskId;
      if (taskId != null) {
        sendTaskAction(taskId, "snooze", 10);
      }
      hideProactiveAlert();
    });
    els.proactiveCloseBtn?.addEventListener("click", (event) => {
      event.stopPropagation();
      hideProactiveAlert();
    });
    els.proactiveAskBtn?.addEventListener("click", (event) => {
      event.stopPropagation();
      triggerProactiveCheck();
    });
    els.stageTaskList?.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-task-action]");
      if (!btn) return;
      event.stopPropagation();
      const action = btn.dataset.taskAction;
      const id = Number(btn.dataset.taskId);
      if (!Number.isFinite(id)) return;
      if (action === "snooze") {
        sendTaskAction(id, "snooze", Number(btn.dataset.minutes || 10));
      } else if (action === "done" || action === "delete" || action === "reopen") {
        sendTaskAction(id, action);
      }
    });
  }

  window.addEventListener("storage", (event) => {
    if (event.key !== STORAGE_KEY || !event.newValue) return;
    try {
      const updated = JSON.parse(event.newValue);
      if (updated.skin && updated.skin !== pet.skin) {
        pet.skin = updated.skin;
        preload(skin());
        if (els.miniThumb) els.miniThumb.src = skin().sprites.idle;
        renderPixel();
        show(current);
        updateStageBadges();
        updateAllMarquees();
        renderSkinCards();
      }
      if (updated.glass && updated.glass !== pet.glass) {
        setGlassMode(updated.glass, { persist: false });
      }
      if (typeof updated.privateMode === "boolean" && updated.privateMode !== pet.privateMode) {
        setPrivateMode(updated.privateMode, { persist: false });
      }
      if (typeof updated.autoExpandEvents === "boolean" && updated.autoExpandEvents !== pet.autoExpandEvents) {
        setAutoExpandMode(updated.autoExpandEvents, { persist: false });
      }
      if (typeof updated.winEventsEnabled === "boolean" && updated.winEventsEnabled !== pet.winEventsEnabled) {
        setWinEventsEnabled(updated.winEventsEnabled, { persist: false });
      }
    } catch {
      /* Ignorar lecturas parciales */
    }
  });

  // ------------------------------------------------------------------ Dynamic Island Top Notch & Resorte de Física (DynamicWin)
  let notchExpanded = false;
  let notchCollapseTimer = null;
  let notchAutoExpandTimer = null;

  // Resorte de segundo orden (física estándar masa-resorte-amortiguador inspirada en DynamicWin).
  function createSpring(initialValue, f = 2.5, z = 0.65, r = 0.1) {
    let k1 = z / (Math.PI * f);
    let k2 = 1 / ((2 * Math.PI * f) ** 2);
    let k3 = (r * z) / (2 * Math.PI * f);
    let y = initialValue;
    let yd = 0;
    let xp = initialValue;
    let tgt = initialValue;

    return {
      setParams(newF, newZ, newR = 0.1) {
        f = newF; z = newZ; r = newR;
        k1 = z / (Math.PI * f);
        k2 = 1 / ((2 * Math.PI * f) ** 2);
        k3 = (r * z) / (2 * Math.PI * f);
      },
      update(target, dt) {
        if (target !== undefined) tgt = target;
        if (dt <= 0) return y;
        const xd = (tgt - xp) / dt;
        xp = tgt;
        const k2s = Math.max(k2, (dt * dt) / 2 + (dt * k1) / 2, dt * k1);
        y += dt * yd;
        yd += (dt * (tgt + k3 * xd - y - k1 * yd)) / k2s;
        return y;
      },
      get value() { return y; },
      get velocity() { return yd; },
      get target() { return tgt; },
      set target(v) { tgt = v; },
      set value(v) { y = v; xp = v; tgt = v; yd = 0; }
    };
  }

  const widthSpring = createSpring(236, 1.1, 0.92, 1.0);
  const heightSpring = createSpring(46, 1.1, 0.92, 1.0);
  const radiusSpring = createSpring(23, 1.1, 0.92, 1.0);

  let springAnimId = null;
  let lastSpringTime = 0;

  function computeExpandedHeight() {
    const maxViewportH = Math.max(176, Math.min((window.innerHeight || 600) - 16, 560));
    const stageStyle = els.stage && typeof getComputedStyle === "function" ? getComputedStyle(els.stage) : null;
    const borderY = stageStyle
      ? ((parseFloat(stageStyle.borderTopWidth) || 0) + (parseFloat(stageStyle.borderBottomWidth) || 0))
      : 0;
    const bottomPad = Math.max(12, parseFloat(stageStyle?.paddingBottom) || 0);
    const topH = els.stageTop?.offsetHeight || 46;

    let shelfTotal = 0;
    if (els.stageShelf) {
      const shelfStyle = typeof getComputedStyle === "function" ? getComputedStyle(els.stageShelf) : null;
      if (!els.stageShelf.hidden && (!shelfStyle || shelfStyle.display !== "none")) {
        const gap = parseFloat(shelfStyle?.rowGap || shelfStyle?.gap) || 8;
        const shelfPadY = shelfStyle
          ? ((parseFloat(shelfStyle.paddingTop) || 0) + (parseFloat(shelfStyle.paddingBottom) || 0))
          : 0;
        let visibleChildren = 0;
        let childrenH = 0;
        for (const child of Array.from(els.stageShelf.children || [])) {
          if (child.hidden || child.hasAttribute?.("hidden")) continue;
          const cs = typeof getComputedStyle === "function" ? getComputedStyle(child) : null;
          if (cs && cs.display === "none") continue;
          const scrollsSelf = cs && (cs.overflowY === "auto" || cs.overflowY === "scroll");
          const childH = scrollsSelf && (child.offsetHeight || 0) > 0
            ? child.offsetHeight
            : Math.max(child.offsetHeight || 0, child.scrollHeight || 0);
          if (childH <= 0) continue;
          const mt = parseFloat(cs?.marginTop) || 0;
          const mb = parseFloat(cs?.marginBottom) || 0;
          childrenH += childH + mt + mb;
          visibleChildren += 1;
        }
        if (visibleChildren > 0) {
          shelfTotal = shelfPadY + childrenH + Math.max(0, visibleChildren - 1) * gap;
        }
      }
    }

    let chatH = 0;
    if (els.chatForm && !els.chatForm.hidden && !els.chatForm.hasAttribute?.("hidden")) {
      const chatStyle = typeof getComputedStyle === "function" ? getComputedStyle(els.chatForm) : null;
      if (!chatStyle || chatStyle.display !== "none") {
        const rawChatH = Math.max(els.chatForm.offsetHeight || 0, els.chatForm.scrollHeight || 0);
        if (rawChatH > 0) {
          const mt = parseFloat(chatStyle?.marginTop) || 0;
          const mb = parseFloat(chatStyle?.marginBottom) || 0;
          chatH = rawChatH + mt + mb;
        }
      }
    }

    const total = borderY + topH + shelfTotal + chatH + bottomPad;
    return Math.round(Math.max(176, Math.min(maxViewportH, total)));
  }

  function requestExpandedHeightUpdate() {
    if (!notchExpanded || heightUpdateRafId !== null) return;
    heightUpdateRafId = requestAnimationFrame(() => {
      heightUpdateRafId = null;
      if (!notchExpanded) return;
      const newTargetH = computeExpandedHeight();
      if (Math.abs((heightSpring.target || 0) - newTargetH) >= 1) {
        heightSpring.setParams(1.1, 0.92, 1.0);
        heightSpring.target = newTargetH;
        if (!springAnimId) {
          startSpring();
        }
      } else if (!springAnimId && els.stage && Math.abs((els.stage.offsetHeight || 0) - newTargetH) >= 1) {
        heightSpring.target = newTargetH;
        startSpring();
      }
    });
  }

  function reportIslandRect() {
    if (!els.stage) return;
    const r = els.stage.getBoundingClientRect();
    if (typeof window.mekaIslandRect === "function") {
      window.mekaIslandRect(r.left, r.top, r.right, r.bottom);
    }
  }

  function reportIslandRectFast(w, h) {
    if (typeof window.mekaIslandRect !== "function") return;
    const winW = window.innerWidth || 400;
    const left = Math.round((winW - w) / 2);
    const top = 8;
    const right = left + Math.round(w);
    const bottom = top + Math.round(h);
    window.mekaIslandRect(left, top, right, bottom);
  }

  function tickSpring(now) {
    if (!lastSpringTime) lastSpringTime = now;
    const dt = Math.min((now - lastSpringTime) / 1000, 0.04);
    lastSpringTime = now;

    const targetW = notchExpanded ? 330 : 236;
    const targetH = notchExpanded ? computeExpandedHeight() : 46;
    const targetR = notchExpanded ? 28 : 23;
    widthSpring.target = targetW;
    heightSpring.target = targetH;
    radiusSpring.target = targetR;

    const currentW = widthSpring.update(targetW, dt);
    const currentH = heightSpring.update(targetH, dt);
    const currentR = radiusSpring.update(targetR, dt);

    if (els.stage) {
      els.stage.style.inlineSize = `${Math.round(currentW * 10) / 10}px`;
      els.stage.style.blockSize = `${Math.round(currentH * 10) / 10}px`;
      els.stage.style.borderRadius = `${Math.round(currentR * 10) / 10}px`;
    }

    reportIslandRectFast(currentW, currentH);

    const diffW = Math.abs(currentW - targetW);
    const diffH = Math.abs(currentH - targetH);
    const isSettled =
      diffW < 0.4 &&
      diffH < 0.4 &&
      Math.abs(widthSpring.velocity) < 1.0 &&
      Math.abs(heightSpring.velocity) < 1.0;

    if (!isSettled) {
      springAnimId = requestAnimationFrame(tickSpring);
    } else {
      if (els.stage) {
        els.stage.style.inlineSize = `${targetW}px`;
        els.stage.style.blockSize = `${targetH}px`;
        els.stage.style.borderRadius = `${targetR}px`;
        els.stage.classList.remove("is-spring-active");
      }
      reportIslandRect();
      springAnimId = null;
      lastSpringTime = 0;
    }
  }

  function startSpring() {
    if (springAnimId) cancelAnimationFrame(springAnimId);
    els.stage?.classList.add("is-spring-active");
    lastSpringTime = 0;
    springAnimId = requestAnimationFrame(tickSpring);
  }

  function canAutoCollapse() {
    if (!notchExpanded) return false;
    if (pendingConfirmId) return false;
    if (skinsCardOpen) return false;
    if (document.activeElement === els.chatInput) return false;
    if (els.chatInput && els.chatInput.value.trim().length > 0) return false;
    if (els.menu && !els.menu.hidden) return false;
    return true;
  }

  function setNotchExpanded(expanded, { force = false, view = null, silent = false } = {}) {
    if (notchExpanded === expanded && !force) return;
    clearTimeout(notchCollapseTimer);

    if (expanded) {
      notchExpanded = true;
      clearIslandSubtlePulse();
      widthSpring.setParams(1.1, 0.92, 1.0);
      heightSpring.setParams(1.1, 0.92, 1.0);
      radiusSpring.setParams(1.1, 0.92, 1.0);

      if (typeof window.mekaSetNotchExpanded === "function") {
        window.mekaSetNotchExpanded(true);
      }
      els.stage?.classList.add("is-expanded");
      document.body?.classList.add("notch-is-expanded");

      // Expand into the card of the requested view, pending confirm, or current active brief
      if (view) {
        setStageView(view);
      } else if (pendingConfirmId) {
        setStageView("hero");
      } else if (!skinsCardOpen) {
        setStageView(briefToStageView(activeBrief));
      }

      if (els.chatForm) {
        els.chatForm.hidden = !notchExpanded || (stageView !== "hero");
      }

      updateStageBadges();
      startSpring();

      if (!silent && stageView === "hero" && !hasDockMessage && !pendingConfirmId) {
        say(pet.sleeping ? line("sleeping") : line("greet"));
      }
    } else {
      if (!force && !canAutoCollapse()) return;

      clearMomentaryExpansionTimer();
      wasCollapsedBeforeMomentary = false;
      if (els.proactiveBanner && !els.proactiveBanner.hidden) {
        activeProactiveAlert = null;
        els.proactiveBanner.hidden = true;
        delete els.proactiveBanner.dataset.kind;
      }

      if (skinsCardOpen) {
        setSkinsCardOpen(false);
      }

      notchExpanded = false;
      if (heightUpdateRafId !== null) {
        cancelAnimationFrame(heightUpdateRafId);
        heightUpdateRafId = null;
      }
      widthSpring.setParams(1.2, 0.96, 0.0);
      heightSpring.setParams(1.2, 0.96, 0.0);
      radiusSpring.setParams(1.2, 0.96, 0.0);

      if (els.chatForm) {
        els.chatForm.hidden = !notchExpanded || (stageView !== "hero");
      }

      els.stage?.classList.remove("is-expanded");
      document.body?.classList.remove("notch-is-expanded");
      startSpring();

      if (typeof window.mekaSetNotchExpanded === "function") {
        window.mekaSetNotchExpanded(false);
      }
    }
  }

  function scheduleNotchCollapse(delay = 450) {
    clearTimeout(notchCollapseTimer);
    notchCollapseTimer = setTimeout(() => {
      setNotchExpanded(false);
    }, delay);
  }

  function expandNotchTemporarily(ttl = 6000) {
    setNotchExpanded(true);
    clearTimeout(notchAutoExpandTimer);
    notchAutoExpandTimer = setTimeout(() => {
      if (!els.stage?.matches(":hover") && canAutoCollapse()) {
        setNotchExpanded(false);
      }
    }, ttl);
  }

  function setupNotch() {
    if (!els.stage) return;

    // Reportar el rectángulo inicial de la Dynamic Island a Go para click-through exacto
    setTimeout(reportIslandRect, 80);
    window.addEventListener("resize", reportIslandRect);

    // Alternar entre píldora y modo desplegado al hacer clic explícito en el notch
    els.stage.addEventListener("click", (event) => {
      if (stageWasDragged) {
        stageWasDragged = false;
        return;
      }
      // Ignorar clics en botones de acción (drawer, menú, chips), inputs, formularios o dots de paginación
      if (event.target.closest("button") || event.target.closest("input") || event.target.closest("form") || event.target.closest(".brief-dots")) return;
      // Si está expandido y el clic es en el cuerpo inferior (mascota, dock), mantener desplegado para interactuar
      if (notchExpanded && !event.target.closest("#stageTop")) return;
      // En modo colapsado: cualquier clic despliega.
      // En modo desplegado: un clic en la cabecera (#stageTop) repliega a píldora.
      setNotchExpanded(!notchExpanded);
    });

    // Auto-colapso suave al salir el cursor o trackpad del área extendida
    els.stage.addEventListener("mouseleave", () => {
      if (wasCollapsedBeforeMomentary) {
        const remaining = Math.max(450, momentaryCollapseAt - Date.now());
        scheduleMomentaryCollapse(remaining);
      } else if (canAutoCollapse()) {
        scheduleNotchCollapse(350);
      }
    });

    // Al pasar el cursor solo mantiene la isla abierta si ya estaba desplegada; nunca auto-despliega
    els.stage.addEventListener("mouseenter", () => {
      clearTimeout(notchCollapseTimer);
    });

    // Si la ventana pierde foco (ej. clic en otra app), replegar automáticamente a píldora
    window.addEventListener("blur", () => {
      if (canAutoCollapse()) {
        scheduleNotchCollapse(200);
      }
    });

    // Clic fuera del contenido (light-dismiss moderno estilo Samsung Brief / dialog)
    document.addEventListener("click", (event) => {
      if (!notchExpanded) return;
      if (!els.stage.contains(event.target) && canAutoCollapse()) {
        setNotchExpanded(false);
      }
    });

    // Tecla Escape para replegar selector, replegar notch o restaurar si estaba oculto para captura
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        if (els.stage?.classList.contains("is-screenshot-hidden")) {
          restoreScreenshotHidden();
        } else if (skinsCardOpen) {
          setSkinsCardOpen(false);
        } else if (notchExpanded) {
          setNotchExpanded(false, { force: true });
        }
      }
    });

    // Mantener expandido y gestionar foco nativo (WS_EX_NOACTIVATE) mientras el chat tenga foco
    const onInputFocus = () => {
      clearTimeout(notchCollapseTimer);
      clearMomentaryExpansionTimer();
      wasCollapsedBeforeMomentary = false;
      setNotchExpanded(true);
      if (typeof window.mekaWantsKeyboard === "function") {
        window.mekaWantsKeyboard(true);
      }
    };
    const onInputBlur = () => {
      if (typeof window.mekaWantsKeyboard === "function") {
        window.mekaWantsKeyboard(false);
      }
      if (!els.stage?.matches(":hover") && canAutoCollapse()) {
        scheduleNotchCollapse(350);
      }
    };
    els.chatInput?.addEventListener("focus", onInputFocus);
    els.chatInput?.addEventListener("blur", onInputBlur);
    const pInput = $("promptInput");
    if (pInput && pInput !== els.chatInput) {
      pInput.addEventListener("focus", onInputFocus);
      pInput.addEventListener("blur", onInputBlur);
    }

    // Delegación global para inputs del Drawer (#coreUrl, #coreToken) y chat
    document.addEventListener("focusin", (event) => {
      if (event.target.matches("input, textarea")) {
        if (typeof window.mekaWantsKeyboard === "function") {
          window.mekaWantsKeyboard(true);
        }
      }
    });
    document.addEventListener("focusout", (event) => {
      if (event.target.matches("input, textarea")) {
        if (typeof window.mekaWantsKeyboard === "function") {
          window.mekaWantsKeyboard(false);
        }
      }
    });

    // Accesos directos rápidos del HUD (estilo DynamicWin Shortcuts)
    els.hudActionGreet?.addEventListener("click", (event) => {
      event.stopPropagation();
      play("greet", line("greet"));
    });
    els.hudActionSleep?.addEventListener("click", (event) => {
      event.stopPropagation();
      if (pet.sleeping) wake();
      else sleep();
    });
    els.hudActionStyle?.addEventListener("click", (event) => {
      event.stopPropagation();
      toggleStyle();
    });

    // Botones switch de Modo Concentración y Liquid Glass (#focusToggleBtn, #focusCardSwitchBtn, #glassToggleBtn, #focusBadge)
    document.addEventListener("click", (event) => {
      const glassBtn = event.target.closest("#glassToggleBtn");
      if (glassBtn) {
        event.stopPropagation();
        setGlassMode(pet.glass === "liquid" ? "normal" : "liquid");
        return;
      }
      const focusBtn = event.target.closest("#focusToggleBtn, #focusCardSwitchBtn");
      if (focusBtn) {
        event.stopPropagation();
        if (focusActive) stopFocus();
        else startFocus();
        return;
      }
      const focusPill = event.target.closest("#focusBadge");
      if (focusPill && focusActive) {
        event.stopPropagation();
        stopFocus();
      }
    });

    // ResizeObserver sobre los hijos de contenido (nunca els.stage directo para evitar bucles durante el resorte)
    if (typeof ResizeObserver === "function") {
      const ro = new ResizeObserver(() => {
        if (notchExpanded) {
          requestExpandedHeightUpdate();
        }
      });
      const observedTargets = [
        els.stageShelf,
        els.stageHero,
        els.stageNotifCard,
        els.stageSkinsCard,
        els.stageFocusCard,
        els.stageSettingsCard,
        els.mediaWidget,
        els.agentReplyDock,
        els.proactiveBanner,
        els.chatForm,
      ];
      for (const target of observedTargets) {
        if (target) ro.observe(target);
      }
    }

    // MutationObserver en #stageShelf para cambios de hidden, open o hijos dinámicos
    if (typeof MutationObserver === "function" && els.stageShelf) {
      const mo = new MutationObserver(() => {
        if (notchExpanded) {
          requestExpandedHeightUpdate();
        }
      });
      mo.observe(els.stageShelf, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["hidden", "open", "data-stage-view"],
      });
    }
  }

  // ------------------------------------------------------------------ Micrófono: Nota de voz Core (/v1/voice) + Web Speech fallback (#promptMic)

  let speechRecognizer = null;
  let speechListening = false;
  let voiceRecorder = null;
  let voiceStream = null;
  let voiceChunks = [];
  let voiceRecording = false;
  let voiceMaxTimer = null;

  function setMicVisualState(active) {
    const micBtn = $("promptMic") || els.promptMic;
    if (micBtn) {
      micBtn.classList.toggle("is-listening", Boolean(active));
      micBtn.setAttribute("aria-pressed", String(Boolean(active)));
    }
  }

  function releaseVoiceStream() {
    clearTimeout(voiceMaxTimer);
    voiceMaxTimer = null;
    voiceRecording = false;
    if (voiceStream) {
      for (const track of voiceStream.getTracks()) {
        try { track.stop(); } catch (_) {}
      }
      voiceStream = null;
    }
    setMicVisualState(false);
  }

  async function uploadVoiceBlob(audioBlob, mimeType) {
    if (!audioBlob || audioBlob.size === 0) return;
    play("thinking", null, { duration: 15_000 });
    updateAgentDock("Procesando nota de voz…", {
      tone: "working",
      badge: pet.privateMode ? "🔒🎙️ Procesando…" : "🎙️ Procesando…",
      animate: "update",
    });

    const ext = mimeType.includes("ogg") ? "voice.ogg" : (mimeType.includes("mp4") ? "voice.m4a" : "voice.webm");
    const form = new FormData();
    form.append("file", audioBlob, ext);
    form.append("session", "ws:pet");
    form.append("user", proactiveUser);
    form.append("audio", "true");
    form.append("private", String(Boolean(pet.privateMode)));

    try {
      const ep = coreHttpEndpoint("/v1/voice");
      const res = await fetch(ep.url, {
        method: "POST",
        headers: ep.headers,
        body: form,
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();
      if (typeof data.transcription === "string" && data.transcription.trim()) {
        logActivity("user.voice", data.transcription.trim());
      } else {
        logActivity("user.voice", "audio nativo enviado");
      }

      const replies = Array.isArray(data.replies) ? data.replies : [];
      const texts = replies.map((r) => (r && typeof r.text === "string" ? r.text.trim() : "")).filter(Boolean);
      const firstReply = replies.find((r) => r && (r.text || r.emotion)) || {};
      const st = normalizeEmotion(firstReply.emotion, firstReply.text) || "happy";

      if (texts.length > 0) {
        play(st, texts.join("\n\n"), {
          directToDock: true,
          dockTone: st === "error" ? "error" : "reply",
          dockBadge: pet.privateMode ? "🔒🎙️ Voz" : "🎙️ Voz",
          forceExpand: Boolean(pet.autoExpandEvents),
        });
      } else {
        show("idle");
        updateAgentDock("Nota de voz recibida.", {
          tone: "reply",
          badge: "🎙️ Voz",
          animate: "update",
        });
      }

      const firstAudio = replies.find((r) => r && r.audio)?.audio;
      if (firstAudio) {
        playAudioClip(firstAudio);
      }
    } catch (err) {
      reportCoreFetchError("/v1/voice", err);
      play("error");
      say("No pude enviar la nota de voz a MEKA Core.", {
        forceExpand: Boolean(pet.autoExpandEvents),
        directToDock: true,
        dockTone: "error",
        dockBadge: "⚠️ Voz",
        pulseState: "error",
      });
    }
  }

  async function startCoreVoiceRecording() {
    voiceStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const candidates = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/ogg;codecs=opus",
    ];
    let mimeType = "";
    if (typeof MediaRecorder.isTypeSupported === "function") {
      mimeType = candidates.find((m) => MediaRecorder.isTypeSupported(m)) || "";
    }
    voiceChunks = [];
    const recorder = mimeType ? new MediaRecorder(voiceStream, { mimeType }) : new MediaRecorder(voiceStream);
    voiceRecorder = recorder;
    voiceRecording = true;
    setMicVisualState(true);
    updateAgentDock("Grabando nota de voz… pulsa de nuevo el micrófono para enviar.", {
      tone: "working",
      badge: "🎙️ Grabando",
      animate: "update",
    });

    recorder.ondataavailable = (ev) => {
      if (ev.data && ev.data.size > 0) {
        voiceChunks.push(ev.data);
      }
    };
    recorder.onerror = () => {
      releaseVoiceStream();
    };
    recorder.onstop = () => {
      const actualMime = recorder.mimeType || mimeType || "audio/webm";
      const blob = new Blob(voiceChunks, { type: actualMime });
      voiceChunks = [];
      voiceRecorder = null;
      releaseVoiceStream();
      if (blob.size > 0) {
        uploadVoiceBlob(blob, actualMime);
      }
    };

    recorder.start();
    voiceMaxTimer = setTimeout(() => {
      if (voiceRecorder && voiceRecorder.state === "recording") {
        try { voiceRecorder.stop(); } catch (_) { releaseVoiceStream(); }
      }
    }, 25_000);
  }

  function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return null;

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = "es-ES";

      recognition.onstart = () => {
        speechListening = true;
        setMicVisualState(true);
      };

      recognition.onend = () => {
        speechListening = false;
        setMicVisualState(false);
      };

      recognition.onerror = () => {
        speechListening = false;
        setMicVisualState(false);
      };

      recognition.onresult = (event) => {
        let transcript = "";
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          transcript += event.results[i][0].transcript;
        }
        const input = $("promptInput") || $("chatInput") || els.chatInput;
        if (input && transcript) {
          input.value = transcript;
          input.dispatchEvent(new Event("input", { bubbles: true }));
          input.focus();
        }
      };

      return recognition;
    } catch (err) {
      console.warn("SpeechRecognition init error:", err);
      return null;
    }
  }

  async function toggleSpeechListening() {
    if (voiceRecording && voiceRecorder) {
      try {
        voiceRecorder.stop();
      } catch (_) {
        releaseVoiceStream();
      }
      return;
    }

    if (core.connected && navigator.mediaDevices?.getUserMedia && typeof window.MediaRecorder === "function") {
      try {
        await startCoreVoiceRecording();
        return;
      } catch {
        releaseVoiceStream();
      }
    }

    if (!speechRecognizer) {
      speechRecognizer = initSpeechRecognition();
    }
    if (!speechRecognizer) {
      say("Reconocimiento de voz no compatible o sin permiso de micrófono 🎙️", {
        directToDock: true,
        dockTone: "error",
        dockBadge: "🎙️ Micrófono",
        forceExpand: Boolean(pet.autoExpandEvents),
        pulseState: "error",
      });
      return;
    }

    if (speechListening) {
      try {
        speechRecognizer.stop();
      } catch (_) {}
    } else {
      try {
        speechRecognizer.start();
      } catch (err) {
        console.warn("SpeechRecognition start error:", err);
      }
    }
  }

  function setupMicrophone() {
    document.addEventListener("click", (event) => {
      const mic = event.target.closest("#promptMic");
      if (!mic) return;
      event.preventDefault();
      event.stopPropagation();
      toggleSpeechListening(mic);
    });
  }

  // ------------------------------------------------------------------ Samsung Brief interacciones (rueda y dots)

  let lastBriefWheelTime = 0;
  const BRIEF_WHEEL_COOLDOWN = 350; // ms (throttle de 350ms para evitar saltos rápidos)

  function handleBriefWheel(event) {
    const isOverPill =
      Boolean(event.target.closest("#skinBadge")) ||
      Boolean(event.target.closest("#stageTop")) ||
      Boolean(event.target.closest(".brief-viewport"));
    if (!isOverPill) return;

    const delta = Math.abs(event.deltaY) >= Math.abs(event.deltaX) ? event.deltaY : event.deltaX;
    if (Math.abs(delta) < 4) return;

    event.preventDefault();

    const now = performance.now();
    if (now - lastBriefWheelTime < BRIEF_WHEEL_COOLDOWN) return;
    lastBriefWheelTime = now;

    clearTimeout(briefPreviewTimer);

    if (delta > 0) {
      stepBrief(1);
    } else {
      stepBrief(-1);
    }
  }

  function setupBriefInteractions() {
    // 1. Wheel listener on #skinBadge y #stageTop con throttle de 350ms
    if (els.stageTop) {
      els.stageTop.addEventListener("wheel", handleBriefWheel, { passive: false });
    }
    if (els.skinBadge && els.skinBadge !== els.stageTop) {
      els.skinBadge.addEventListener("wheel", handleBriefWheel, { passive: false });
    }

    // 2. Click listener en #briefDots para cambiar directamente de tarjeta (compatibilidad si existe)
    if (els.briefDots) {
      els.briefDots.addEventListener("click", (event) => {
        event.stopPropagation();
        const dot = event.target.closest("[data-brief-dot]");
        if (dot) {
          const target = dot.dataset.briefDot;
          if (target) {
            clearTimeout(briefPreviewTimer);
            pinUserBrief(target);
            setActiveBrief(target);
          }
        }
      });
    }

    // 3. Click listener en #stageNotifList para acciones de notificación (open / dismiss)
    if (els.stageNotifList) {
      els.stageNotifList.addEventListener("click", (event) => {
        const btn = event.target.closest("button[data-action]");
        if (!btn) return;
        event.stopPropagation();
        const action = btn.dataset.action;
        const id = Number(btn.dataset.id);
        if (id == null || isNaN(id)) return;
        if (action === "dismiss") {
          dismissNotification(id);
        } else if (action === "open") {
          openNotification(id);
        }
      });
    }

    // 4. Click listener en botón de limpiar todas (#notifClearAllBtn)
    if (els.notifClearAllBtn) {
      els.notifClearAllBtn.addEventListener("click", (event) => {
        event.stopPropagation();
        clearAllNotifications();
      });
    }

    // 5. Click listeners contextuales en las tarjetas de brief para desplegar la vista correspondiente
    if (els.briefAvatar) {
      els.briefAvatar.addEventListener("click", (event) => {
        event.stopPropagation();
        clearTimeout(briefPreviewTimer);
        pinUserBrief("avatar");
        setActiveBrief("avatar");
        setNotchExpanded(true);
      });
    }
    if (els.briefMedia) {
      els.briefMedia.addEventListener("click", (event) => {
        event.stopPropagation();
        clearTimeout(briefPreviewTimer);
        pinUserBrief("media");
        setActiveBrief("media");
        setNotchExpanded(true);
      });
    }
    if (els.briefNotif) {
      els.briefNotif.addEventListener("click", (event) => {
        event.stopPropagation();
        clearTimeout(briefPreviewTimer);
        pinUserBrief("notif");
        setActiveBrief("notif");
        setNotchExpanded(true);
      });
    }

    // 6. Recalcular marquees en resize de ventana
    window.addEventListener("resize", () => {
      updateAllMarquees();
    });

    // Render inicial del inbox de notificaciones
    renderNotifInbox();

    // Estado inicial en brief avatar
    setActiveBrief("avatar", { animate: false });
  }

  // ------------------------------------------------------------------ arranque

  function start() {
    document.documentElement.classList.toggle("desktop", hasNativeHost() || IS_DESKTOP);
    const skinParam = params.get("skin");
    if (skinParam && CATALOG.skins[skinParam]) {
      pet.skin = skinParam;
    }
    setupSkinsSelector();
    setupControls();
    setupNotch();
    setupBriefInteractions();
    syncIslandIllumination({ animate: false });
    setupMicrophone();
    setupLivingAvatarInteractions();

    // Estado inicial sincronizado de vistas contextuales
    ensureBubbleAlwaysHidden();
    if (els.confirmBar && !pendingConfirmId) els.confirmBar.hidden = true;
    if (els.bubbleTag && !pendingConfirmId) els.bubbleTag.hidden = true;
    setStageView(briefToStageView(activeBrief));
    if (els.miniMusicBar) els.miniMusicBar.hidden = true;
    if (els.hudBatteryChip) els.hudBatteryChip.hidden = true;

    preload(skin());
    if (els.miniThumb) els.miniThumb.src = skin().sprites.idle;
    renderPixel();
    show(base);

    // Actualizar marquees una vez renderizado el estado inicial
    updateAllMarquees();

    const coreUrl = params.get("core") || DEFAULT_CORE_URL;
    const token = params.get("token") || "";
    if ($("coreUrl") && params.get("core")) $("coreUrl").value = coreUrl;
    if (els.coreToken && token) els.coreToken.value = token;
    updateFocusUI();
    connectCore(coreUrl, token);
    if (typeof window.mekaNotifyReady === "function") {
      try {
        window.mekaNotifyReady();
      } catch (_) {}
    }
  }

  window.MEKA = {
    emit: handleEvent,
    emitNativeEvent,
    state: () => ({
      ...pet,
      current,
      base,
      activeBrief,
      stageView,
      focusActive,
      focusUntil,
      notifications: [...notificationInbox],
      pendingTasks: [...pendingTasks],
      activeProactiveAlert,
    }),
    setBrief: setActiveBrief,
    cycleBrief: stepBrief,
    toggleNotch: () => setNotchExpanded(!notchExpanded),
    syncAutoStartUI,
    openNotification,
    dismissNotification,
    clearAllNotifications,
    getNotificationEmoji,
    getNotificationBrandSpec,
    checkAndApplyMarquee,
    updateAllMarquees,
    setStageView,
    setSkinsCardOpen,
    setGlassMode,
    setAutoExpandMode,
    setWinEventsEnabled,
    setState,
    normalizeEmotion,
    triggerTempBodyMotion,
    spawnParticles,
    spawnMiniParticles,
    startMiniParticles,
    triggerIslandSubtlePulse,
    triggerIslandMediaGlow,
    syncIslandIllumination,
    applySystemMedia,
    showProactiveAlert,
    hideProactiveAlert,
    triggerMomentaryExpansion,
    fetchPendingTasks,
    sendTaskAction,
    triggerProactiveCheck,
    toggleSpeechListening,
    startFocus,
    stopFocus,
    computeExpandedHeight,
  };

  start();
})();
