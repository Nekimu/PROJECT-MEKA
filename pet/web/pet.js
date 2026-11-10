/* MEKA · motor de la mascota (prototipo). Sin dependencias ni compilación.
 *
 * - Máquina de estados: estado base (idle / working / sleeping) + estados temporales.
 * - Tamagotchi no punitivo: las estadísticas bajan con el tiempo pero nunca de STAT_MIN.
 * - Eventos de MEKA Core por WebSocket (ver docs/VISION.md → "Contrato de eventos").
 * - Funciona en el navegador (con panel de pruebas) y en Tauri (ventana transparente).
 */
(() => {
  "use strict";

  const CATALOG = window.MEKA_SKINS;
  const STORAGE_KEY = "meka.pet.v1";
  const TAURI = window.__TAURI__ || null;
  const params = new URLSearchParams(location.search);
  const IS_DESKTOP = Boolean(TAURI) || params.has("desktop");
  const STAT_MIN = 5;
  const STAT_MAX = 100;
  const MAX_OFFLINE_HOURS = 48;
  const DEFAULT_CORE_URL = "ws://127.0.0.1:8765/v1/events";

  // Variación por hora de juego. Con hambre o cansancio el ánimo baja el doble.
  const RATES = { saciedad: -6, animo: -3, afecto: -0.5, energiaDespierta: -4, energiaDormida: 15 };

  // Animación de cada estado: movimiento CSS, partículas y duración si es temporal.
  const FX = {
    idle: { motion: "breathe" },
    happy: { motion: "bounce", particle: "💖", every: 380, duration: 2600 },
    working: { motion: "sway", particle: "⚡", every: 1300 },
    thinking: { motion: "tilt", particle: "💭", every: 1600, duration: 6000 },
    sleeping: { motion: "sleep", particle: "z", every: 1000, dim: true },
    eating: { motion: "munch", particle: "food", every: 450, duration: 2800 },
    error: { motion: "shake", particle: "💦", every: 500, duration: 3200 },
    celebrate: { motion: "jump", particle: "✨", every: 300, duration: 3200 },
    sad: { motion: "droop", particle: "💧", every: 900, duration: 3500 },
  };

  const SAMPLE_EVENTS = [
    ["📂 Agente trabajando", { type: "agent.working", data: { task: "Ordenar la carpeta Descargas" } }],
    ["✅ Tarea completada", { type: "agent.done", data: { summary: "¡Listo! Ordené 42 archivos en 6 carpetas 🎉" } }],
    ["❌ Error", { type: "agent.error", data: { message: "No pude abrir presupuesto.xlsx 💦" } }],
    ["🔐 Pedir permiso", { type: "agent.confirm", data: { action: "borrar 3 archivos duplicados" } }],
    ["💬 Mensaje", { type: "message", data: { text: "¡Te llegó un mensaje por Telegram! 💌", emotion: "happy" } }],
    ["🤔 Pensando", { type: "emotion", data: { emotion: "thinking" } }],
    ["💸 Sin créditos", { type: "budget.low", data: {} }],
  ];

  // ------------------------------------------------------------------ utilidades

  const $ = (id) => document.getElementById(id);
  const pick = (list) => list[Math.floor(Math.random() * list.length)];
  const clamp = (value) => Math.min(STAT_MAX, Math.max(STAT_MIN, value));

  const els = {
    stage: $("stage"), pet: $("pet"), body: $("petBody"), img: $("sprite"), pixel: $("pixelSprite"),
    particles: $("particles"), bubble: $("bubble"), stats: $("statsMini"), menu: $("menu"),
    chatForm: $("chatForm"), chatInput: $("chatInput"), panel: $("panel"),
  };

  // ------------------------------------------------------------------ estado persistente

  function defaults() {
    return {
      skin: CATALOG.default,
      style: "anime",
      stats: { energia: 80, saciedad: 70, animo: 70, afecto: 30 },
      sleeping: false,
      showStats: false,
      unlocked: {},
      unlockedAll: false,
      lastTick: Date.now(),
      lastInteraction: Date.now(),
    };
  }

  function load() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (saved && saved.stats) {
        const base = defaults();
        return { ...base, ...saved, stats: { ...base.stats, ...saved.stats } };
      }
    } catch {
      /* Almacenamiento no disponible o corrupto: se empieza de cero */
    }
    return defaults();
  }

  function save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(pet));
    } catch {
      /* Modo privado o almacenamiento bloqueado: la mascota funciona igual */
    }
  }

  const pet = load();
  if (!CATALOG.skins[pet.skin]) pet.skin = CATALOG.default;

  // ------------------------------------------------------------------ estado en ejecución

  let base = pet.sleeping ? "sleeping" : "idle"; // estado al que se vuelve tras uno temporal
  let current = base;
  let agentWorking = false;
  let sleepWasAuto = pet.sleeping;
  let transientTimer = null;
  let particleTimer = null;
  let bubbleTimer = null;
  let typeTimer = null;
  let speed = 1;
  let lastFrame = Date.now();
  let lastPet = 0;
  let lastNag = Date.now();

  const skin = () => CATALOG.skins[pet.skin] || CATALOG.skins[CATALOG.default];
  const line = (kind) => pick(skin().lines[kind] || skin().lines.idle);
  const validState = (name) => (Object.hasOwn(FX, name) ? name : null);
  const touch = () => { pet.lastInteraction = Date.now(); };
  const bump = (stat, delta) => { pet.stats[stat] = clamp(pet.stats[stat] + delta); };

  // ------------------------------------------------------------------ sprites y estilo

  function spriteFor(state) {
    const sk = skin();
    const key = pick(sk.states[state] || sk.states.idle);
    return sk.sprites[key] || sk.sprites.idle;
  }

  function setSprite(src) {
    if (els.img.getAttribute("src") !== src) els.img.src = src;
    else renderPixel();
  }

  function preload(sk) {
    for (const src of Object.values(sk.sprites)) new Image().src = src;
  }

  // Estilo "pixel art": reduce el sprite a 64 px de ancho, limita la paleta y lo
  // escala sin suavizado. Sirve para comparar estilos antes de encargar arte.
  function renderPixel() {
    const isPixel = pet.style === "pixel";
    els.img.hidden = isPixel;
    els.pixel.hidden = !isPixel;
    if (!isPixel || !els.img.naturalWidth) return;

    const width = 64;
    const height = Math.round((width * els.img.naturalHeight) / els.img.naturalWidth);
    els.pixel.width = width;
    els.pixel.height = height;
    const ctx = els.pixel.getContext("2d");
    ctx.clearRect(0, 0, width, height);
    ctx.drawImage(els.img, 0, 0, width, height);
    try {
      const image = ctx.getImageData(0, 0, width, height);
      const d = image.data;
      for (let i = 0; i < d.length; i += 4) {
        d[i + 3] = d[i + 3] < 110 ? 0 : 255; // contorno nítido
        for (let c = 0; c < 3; c++) d[i + c] = Math.round(d[i + c] / 36) * 36; // paleta reducida
      }
      ctx.putImageData(image, 0, 0);
    } catch {
      /* Abierto con file://: el navegador no deja leer píxeles; queda solo el pixelado */
    }
  }

  els.img.addEventListener("load", renderPixel);

  // ------------------------------------------------------------------ máquina de estados

  function show(state) {
    current = state;
    const fx = FX[state];
    els.body.dataset.motion = fx.motion;
    els.pet.classList.toggle("is-dim", Boolean(fx.dim));
    setSprite(spriteFor(state));
    startParticles(fx.particle, fx.every);
  }

  function play(state, text, { particle, duration } = {}) {
    if (pet.sleeping && state !== "sleeping") wake({ quiet: true });
    clearTimeout(transientTimer);
    transientTimer = null;
    show(state);
    if (particle) startParticles(particle, 400);
    const ms = duration ?? FX[state].duration;
    if (ms) {
      transientTimer = setTimeout(() => {
        transientTimer = null;
        show(base);
      }, ms);
    }
    if (text) say(text);
  }

  function setBase(state, { interrupt = false } = {}) {
    base = state;
    if (interrupt) {
      clearTimeout(transientTimer);
      transientTimer = null;
    }
    if (!transientTimer) show(state);
  }

  function sleep({ auto = false } = {}) {
    pet.sleeping = true;
    sleepWasAuto = auto;
    clearTimeout(transientTimer);
    transientTimer = null;
    setBase("sleeping");
    say(line("sleeping"));
    save();
  }

  function wake({ quiet = false } = {}) {
    pet.sleeping = false;
    sleepWasAuto = false;
    setBase(agentWorking ? "working" : "idle");
    if (!quiet) say(line("wake"));
    save();
  }

  // ------------------------------------------------------------------ partículas y bocadillo

  function startParticles(kind, every = 450) {
    clearInterval(particleTimer);
    particleTimer = null;
    if (!kind) return;
    const spawn = () => {
      const el = document.createElement("span");
      el.className = kind === "z" ? "particle particle--z" : "particle";
      el.textContent = kind === "food" ? pick(skin().food) : kind === "z" ? pick(["z", "Z", "z"]) : kind;
      el.style.left = `${20 + Math.random() * 60}%`;
      el.style.setProperty("--dx", `${Math.round((Math.random() - 0.5) * 60)}px`);
      el.addEventListener("animationend", () => el.remove());
      els.particles.append(el);
    };
    spawn();
    particleTimer = setInterval(spawn, every);
  }

  function say(text, ms) {
    if (!text) return;
    clearTimeout(bubbleTimer);
    clearInterval(typeTimer);
    const chars = Array.from(text);
    let i = 0;
    els.bubble.textContent = "";
    els.bubble.hidden = false;
    typeTimer = setInterval(() => {
      els.bubble.textContent += chars[i++] ?? "";
      if (i >= chars.length) clearInterval(typeTimer);
    }, 22);
    bubbleTimer = setTimeout(() => { els.bubble.hidden = true; }, ms || Math.min(9000, 2600 + chars.length * 60));
  }

  // ------------------------------------------------------------------ Tamagotchi

  function advance(hours) {
    const s = pet.stats;
    const strained = s.saciedad < 25 || s.energia < 20;
    s.saciedad += RATES.saciedad * hours;
    s.animo += RATES.animo * hours * (strained ? 2 : 1);
    s.afecto += RATES.afecto * hours;
    s.energia += (pet.sleeping ? RATES.energiaDormida : RATES.energiaDespierta) * hours;
    for (const key of Object.keys(s)) s[key] = clamp(s[key]);
  }

  function isUnlocked(id) {
    const sk = CATALOG.skins[id];
    return pet.unlockedAll || pet.unlocked[id] || sk.unlockAt <= pet.stats.afecto;
  }

  function checkUnlocks() {
    for (const [id, sk] of Object.entries(CATALOG.skins)) {
      if (sk.unlockAt > 0 && !pet.unlocked[id] && sk.unlockAt <= pet.stats.afecto) {
        pet.unlocked[id] = true; // Una vez desbloqueado no se vuelve a bloquear
        play("celebrate", `¡Desbloqueaste a ${sk.name}! Búscalo en el menú ✨`);
        save();
      }
    }
  }

  // Comportamiento autónomo: dormir, pedir comida, quejarse de cansancio...
  function autonomy(now) {
    const s = pet.stats;
    if (pet.sleeping) {
      if (sleepWasAuto && s.energia >= 98) wake();
      return;
    }
    if (base !== "idle" || transientTimer) return;

    const night = new Date().getHours() < 7;
    if (s.energia < 12 || (night && now - pet.lastInteraction > 10 * 60_000)) {
      sleep({ auto: true });
      return;
    }

    const cooldown = 120_000 / Math.min(speed, 20);
    if (now - lastNag < cooldown) return;
    lastNag = now;
    if (s.saciedad < 25) say(line("hungry"));
    else if (s.energia < 25) say(line("tired"));
    else if (s.animo < 25) play("sad", line("sad"));
    else if (Math.random() < 0.25) say(line("idle"));
  }

  // ------------------------------------------------------------------ acciones del usuario

  function onPetClick() {
    touch();
    if (pet.sleeping) {
      wake();
      return;
    }
    const now = Date.now();
    if (now - lastPet < 700) return;
    lastPet = now;
    bump("animo", 6);
    bump("afecto", 1);
    play("happy", line("happy"));
    checkUnlocks();
  }

  function feed() {
    touch();
    if (pet.stats.saciedad > 92) {
      say(line("full"));
      return;
    }
    bump("saciedad", 30);
    bump("animo", 4);
    play("eating", line("eating"));
  }

  function playGame() {
    touch();
    if (pet.stats.energia < 15) {
      say(line("tired"));
      return;
    }
    bump("animo", 10);
    bump("afecto", 1);
    bump("energia", -6);
    play("happy", "¡Una partida más! 🎮", { particle: "🎮" });
    checkUnlocks();
  }

  function setSkin(id) {
    if (!CATALOG.skins[id] || !isUnlocked(id)) return;
    pet.skin = id;
    preload(skin());
    show(current);
    say(line("greet"));
    save();
  }

  function toggleStyle() {
    pet.style = pet.style === "pixel" ? "anime" : "pixel";
    renderPixel();
    save();
  }

  function toggleStats() {
    pet.showStats = !pet.showStats;
    els.stats.classList.toggle("is-visible", pet.showStats);
    save();
  }

  // ------------------------------------------------------------------ chat

  function openChat() {
    els.chatForm.hidden = false;
    els.chatInput.value = "";
    els.chatInput.focus();
  }

  els.chatForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const text = els.chatInput.value.trim();
    els.chatForm.hidden = true;
    if (!text) return;
    touch();
    bump("animo", 2);
    if (core.connected) {
      core.send({ type: "user.message", data: { text } });
      play("thinking", null, { duration: 15_000 }); // Hasta que llegue la respuesta
    } else {
      play("thinking");
      setTimeout(() => play("happy", line("chat")), 1400);
    }
  });

  els.chatInput.addEventListener("keydown", (event) => {
    if (event.key === "Escape") els.chatForm.hidden = true;
  });

  // ------------------------------------------------------------------ menú contextual

  function menuItems() {
    const items = [
      ["🍙 Alimentar", feed],
      ["🎮 Jugar", playGame],
      [pet.sleeping ? "☀️ Despertar" : "😴 Dormir", () => (pet.sleeping ? wake() : sleep())],
      ["💬 Hablar", openChat],
      "sep",
      "Personaje",
    ];
    for (const [id, sk] of Object.entries(CATALOG.skins)) {
      const locked = !isUnlocked(id);
      const label = `${id === pet.skin ? "✓ " : ""}${sk.name}${locked ? ` 🔒 afecto ${sk.unlockAt}` : ""}`;
      items.push([label, () => setSkin(id), locked]);
    }
    items.push(
      "sep",
      [pet.style === "pixel" ? "🖼️ Estilo anime" : "👾 Estilo pixel art", toggleStyle],
      [pet.showStats ? "📊 Ocultar estado" : "📊 Mostrar estado", toggleStats],
    );
    if (TAURI) items.push("sep", ["✖ Cerrar", () => TAURI.window.getCurrentWindow().close()]);
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
        const [label, action, disabled] = item;
        const button = document.createElement("button");
        button.type = "button";
        button.setAttribute("role", "menuitem");
        button.textContent = label;
        button.disabled = Boolean(disabled);
        button.addEventListener("click", () => {
          closeMenu();
          action();
          renderStats();
          save();
        });
        li.append(button);
      }
      els.menu.append(li);
    }
    els.menu.hidden = false;
    const stage = els.stage.getBoundingClientRect();
    const left = Math.min(Math.max(clientX - stage.left, 8), stage.width - els.menu.offsetWidth - 8);
    const top = Math.min(Math.max(clientY - stage.top, 8), stage.height - els.menu.offsetHeight - 8);
    els.menu.style.left = `${Math.max(8, left)}px`;
    els.menu.style.top = `${Math.max(8, top)}px`;
    els.menu.querySelector("button:not([disabled])")?.focus();
  }

  function closeMenu() {
    els.menu.hidden = true;
  }

  document.addEventListener("pointerdown", (event) => {
    if (!els.menu.hidden && !els.menu.contains(event.target)) closeMenu();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenu();
  });

  // ------------------------------------------------------------------ puntero: acariciar, arrastrar, menú

  const offset = { x: 0, y: 0 };
  let press = null;

  function startWindowDrag() {
    TAURI?.window.getCurrentWindow().startDragging().catch(() => {});
  }

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
      touch();
      if (TAURI) {
        // En escritorio se mueve la ventana entera
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

  // ------------------------------------------------------------------ eventos de MEKA Core

  const EVENTS = {
    "agent.working": (d) => {
      agentWorking = true;
      if (pet.sleeping) wake({ quiet: true });
      setBase("working", { interrupt: true }); // Un evento del agente se ve al instante
      say(d.task ? `Trabajando en: ${d.task} 📂` : line("working"));
    },
    "agent.done": (d) => {
      agentWorking = false;
      if (!pet.sleeping) base = "idle";
      bump("animo", 8);
      bump("afecto", 2);
      play("celebrate", d.summary || line("celebrate"));
      checkUnlocks();
    },
    "agent.error": (d) => {
      agentWorking = false;
      if (!pet.sleeping) base = "idle";
      bump("animo", -5);
      play("error", d.message || line("error"));
    },
    "agent.confirm": (d) => {
      play("thinking", `¿Me das permiso para ${d.action || "continuar"}? Confírmalo en tu móvil 📱`);
    },
    message: (d) => play(validState(d.emotion) || "happy", d.text),
    emotion: (d) => {
      const state = validState(d.emotion);
      if (state) play(state);
    },
    "budget.low": () => play("sad", line("broke")),
  };

  function handleEvent(event) {
    const handler = event && EVENTS[event.type];
    if (!handler) {
      console.warn("Evento desconocido de MEKA Core:", event);
      return;
    }
    handler(event.data || {});
    renderStats();
    save();
  }

  // ------------------------------------------------------------------ conexión WebSocket

  const core = { ws: null, connected: false, retry: 1000, timer: null };
  core.send = (message) => {
    if (core.connected) core.ws.send(JSON.stringify(message));
  };

  function setCoreStatus(text) {
    const el = $("coreStatus");
    if (el) el.textContent = text;
  }

  function connectCore(url) {
    clearTimeout(core.timer);
    if (core.ws) {
      core.ws.onclose = null;
      core.ws.close();
    }
    setCoreStatus("conectando…");
    let ws;
    try {
      ws = new WebSocket(url);
    } catch {
      setCoreStatus("URL no válida o bloqueada por el navegador");
      return;
    }
    core.ws = ws;
    ws.onopen = () => {
      core.connected = true;
      core.retry = 1000;
      setCoreStatus("conectado ✅");
      core.send({ type: "client.hello", data: { client: "pet", skin: pet.skin } });
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
      setCoreStatus(`sin conexión · reintento en ${core.retry / 1000} s`);
      core.timer = setTimeout(() => connectCore(url), core.retry);
      core.retry = Math.min(core.retry * 2, 30_000);
    };
  }

  // ------------------------------------------------------------------ panel de pruebas (navegador)

  function renderStats() {
    for (const el of els.stats.querySelectorAll(".stat")) {
      const value = pet.stats[el.dataset.stat];
      el.querySelector("i").style.setProperty("--value", `${value}%`);
      el.classList.toggle("is-low", value < 25);
    }
    for (const [key, value] of Object.entries(pet.stats)) {
      const dd = document.querySelector(`[data-number="${key}"]`);
      if (dd) dd.textContent = Math.round(value);
    }
  }

  function setupPanel() {
    const buttons = $("eventButtons");
    for (const [label, event] of SAMPLE_EVENTS) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.addEventListener("click", () => handleEvent(structuredClone(event)));
      buttons.append(button);
    }

    const numbers = $("statsNumbers");
    const names = { energia: "⚡ Energía", saciedad: "🍙 Saciedad", animo: "😊 Ánimo", afecto: "💙 Afecto" };
    for (const [key, name] of Object.entries(names)) {
      const wrap = document.createElement("div");
      const dt = document.createElement("dt");
      const dd = document.createElement("dd");
      dt.textContent = name;
      dd.dataset.number = key;
      wrap.append(dt, dd);
      numbers.append(wrap);
    }

    $("speed").addEventListener("change", (event) => { speed = Number(event.target.value); });
    $("unlockAll").addEventListener("click", () => {
      pet.unlockedAll = true;
      play("celebrate", "¡Personajes desbloqueados! (modo demo) 🔓");
      save();
    });
    $("resetPet").addEventListener("click", () => {
      Object.assign(pet, defaults());
      agentWorking = false;
      base = "idle";
      offset.x = offset.y = 0;
      els.pet.style.translate = "";
      els.stats.classList.remove("is-visible");
      renderPixel();
      show("idle");
      say(line("greet"));
      renderStats();
      save();
    });
    $("coreForm").addEventListener("submit", (event) => {
      event.preventDefault();
      connectCore($("coreUrl").value.trim());
    });
  }

  // ------------------------------------------------------------------ arranque

  function start() {
    document.documentElement.classList.toggle("desktop", IS_DESKTOP);

    // Lo que pasó mientras la app estaba cerrada (como un Tamagotchi de verdad)
    const awayHours = Math.min((Date.now() - pet.lastTick) / 3_600_000, MAX_OFFLINE_HOURS);
    if (awayHours > 0) advance(awayHours);

    preload(skin());
    els.stats.classList.toggle("is-visible", pet.showStats);
    show(base);
    renderStats();
    if (!IS_DESKTOP) setupPanel();
    setTimeout(() => say(pet.sleeping ? line("sleeping") : line("greet")), 500);

    const coreUrl = params.get("core") || (TAURI ? DEFAULT_CORE_URL : null);
    if (coreUrl) connectCore(coreUrl);

    setInterval(() => {
      const now = Date.now();
      advance(((now - lastFrame) / 3_600_000) * speed);
      lastFrame = now;
      pet.lastTick = now;
      autonomy(now);
      renderStats();
    }, 1000);
    setInterval(save, 5000);
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) save();
    });
    window.addEventListener("pagehide", save);
  }

  // API para pruebas desde la consola y para MEKA Core embebido: MEKA.emit({type, data})
  window.MEKA = { emit: handleEvent, state: () => ({ ...pet, current, base }) };

  start();
})();
