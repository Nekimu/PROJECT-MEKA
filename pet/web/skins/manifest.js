// Personajes de la mascota. Todo lo que sigue a la asignación es JSON puro:
// tests/test_pet_skins.py lo valida (estados completos y sprites existentes).
// Se carga como <script> clásico para que index.html funcione también con doble clic.
window.MEKA_SKINS = {
  "default": "meka",
  "states": ["idle", "happy", "working", "thinking", "sleeping", "eating", "error", "celebrate", "sad"],
  "skins": {
    "meka": {
      "name": "MEKA",
      "description": "Compañera original de visor (nombre provisional).",
      "unlockAt": 0,
      "sprites": {
        "idle": "skins/meka/idle.webp",
        "happy": "skins/meka/happy.webp",
        "working": "skins/meka/working.webp"
      },
      "states": {
        "idle": ["idle"], "happy": ["happy"], "working": ["working"], "thinking": ["idle"],
        "sleeping": ["idle"], "eating": ["happy"], "error": ["working"], "celebrate": ["happy"], "sad": ["idle"]
      },
      "food": ["🍙", "🍡", "🧋"],
      "lines": {
        "greet": ["¡Hola! ¿Qué proyecto tocamos hoy? ✨", "¡Volviste! Te estaba esperando 💙"],
        "idle": ["Aquí estoy, vigilando tus carpetas 👀", "¿Una partida rápida antes de seguir?", "Si necesitas algo, solo tócame ✨"],
        "happy": ["¡Jeje, eso me gusta! 💙", "¡Más mimos, por fa!", "Contigo todo es más divertido ✨"],
        "working": ["Cazando bugs... ¡déjamelo a mí! ⚔️", "Ordenando archivos, un segundito 📂"],
        "thinking": ["Mmm... déjame pensarlo 💭", "Procesando... 🧠"],
        "sleeping": ["Zzz... cinco minutitos más..."],
        "wake": ["¡Ah! Estaba soñando con píxeles 😳", "¡Ya estoy despierta!"],
        "eating": ["¡Ñam! Gracias 🍙", "¡Delicioso! Recargando energía ⚡"],
        "full": ["Estoy llenísima, guárdalo para luego 🫃"],
        "error": ["¡Un bug salvaje apareció! 🐞", "Algo salió mal... lo reviso contigo 💦"],
        "celebrate": ["¡Misión cumplida! 🎉", "¡Lo logramos! ✨"],
        "sad": ["Me siento un poco sola... 💧"],
        "hungry": ["Tengo un poquito de hambre... 🍙"],
        "tired": ["Estoy agotada, ¿me dejas descansar? 😴"],
        "broke": ["Nos quedamos sin créditos de la API... 💸"],
        "chat": ["Cuando conecte con MEKA Core te responderé de verdad 💭", "¡Anotado! En cuanto tenga cerebro te contesto ✨"]
      }
    },
    "nekimu": {
      "name": "Nekimu",
      "description": "Tu avatar: modo desarrollador.",
      "unlockAt": 0,
      "sprites": {
        "idle": "skins/nekimu/idle.webp",
        "happy": "skins/nekimu/happy.webp",
        "working": "skins/nekimu/working.webp",
        "thinking": "skins/nekimu/thinking.webp",
        "sleeping": "skins/nekimu/sleeping.webp",
        "eating": "skins/nekimu/eating.webp",
        "eating2": "skins/nekimu/eating2.webp",
        "error": "skins/nekimu/error.webp",
        "celebrate": "skins/nekimu/celebrate.webp",
        "sad": "skins/nekimu/sad.webp"
      },
      "states": {
        "idle": ["idle"], "happy": ["happy"], "working": ["working"], "thinking": ["thinking"],
        "sleeping": ["sleeping"], "eating": ["eating", "eating2"], "error": ["error"],
        "celebrate": ["celebrate"], "sad": ["sad"]
      },
      "food": ["🌮", "🍔", "☕"],
      "lines": {
        "greet": ["¿Qué rompemos hoy? 😎", "Café listo, compilador listo ☕"],
        "idle": ["Todo compila... sospechoso 🤨", "¿Y si refactorizamos? 👀"],
        "happy": ["¡Así sí da gusto programar! 🔥"],
        "working": ["Modo concentración: ON 🔥", "No me hables, estoy en la zona 💻"],
        "thinking": ["Analizando... ¿eso es un aguacate? 🥑", "Leyendo la documentación (por fin) 📖"],
        "sleeping": ["Zzz... lunes otra vez..."],
        "wake": ["¡Estaba compilando mentalmente! 😅"],
        "eating": ["¡DELICIOSO! 🌮", "Un taco y lo arreglo todo 🌮"],
        "full": ["No me cabe ni un commit más 🍔"],
        "error": ["SQL ERROR... ¿quién tocó producción? 😱", "¡No es un bug, es una feature! 💦"],
        "celebrate": ["¡PAYDAY! 💸", "¡Deploy exitoso! 🚀"],
        "sad": ["La cartera vacía y el bug vivo... 💸"],
        "hungry": ["Necesito tacos para seguir 🌮"],
        "tired": ["Necesito café... mucho café ☕"],
        "broke": ["Se acabaron los créditos de la API 💸"],
        "chat": ["Cuando conecte con MEKA Core te contesto en serio 💬"]
      }
    },
    "espadachina": {
      "name": "Espadachina",
      "description": "Guerrera de coleta (boceto: una sola pose).",
      "unlockAt": 50,
      "sprites": {"idle": "skins/espadachina/idle.webp"},
      "states": {
        "idle": ["idle"], "happy": ["idle"], "working": ["idle"], "thinking": ["idle"], "sleeping": ["idle"],
        "eating": ["idle"], "error": ["idle"], "celebrate": ["idle"], "sad": ["idle"]
      },
      "food": ["🍵", "🍙"],
      "lines": {
        "greet": ["Mi espada está a tu servicio."],
        "idle": ["Vigilo tus proyectos. Nada pasará sin que lo sepa."],
        "happy": ["...Gracias. No se lo digas a nadie."],
        "working": ["Cortando la tarea en partes pequeñas ⚔️"],
        "thinking": ["Estudio al enemigo antes de atacar."],
        "sleeping": ["Zzz..."],
        "wake": ["¡En guardia!"],
        "eating": ["Un buen guerrero no salta comidas."],
        "full": ["Suficiente. La disciplina ante todo."],
        "error": ["Un fallo. Lo enfrentaremos juntos."],
        "celebrate": ["Victoria. Bien hecho."],
        "sad": ["Hasta las espadas descansan..."],
        "hungry": ["El estómago también libra batallas."],
        "tired": ["Necesito afilar fuerzas... y dormir."],
        "broke": ["Sin recursos no hay campaña."],
        "chat": ["Habla. Te escucharé cuando tenga cerebro."]
      }
    },
    "kitsune": {
      "name": "Kitsune",
      "description": "Sacerdotisa zorro (boceto: una sola pose).",
      "unlockAt": 70,
      "sprites": {"idle": "skins/kitsune/idle.webp"},
      "states": {
        "idle": ["idle"], "happy": ["idle"], "working": ["idle"], "thinking": ["idle"], "sleeping": ["idle"],
        "eating": ["idle"], "error": ["idle"], "celebrate": ["idle"], "sad": ["idle"]
      },
      "food": ["🍡", "🦊", "🍥"],
      "lines": {
        "greet": ["Los espíritus del zorro te saludan 🦊"],
        "idle": ["Siento buena energía en tus carpetas ✨"],
        "happy": ["¡Kon kon! 🦊"],
        "working": ["Purificando archivos desordenados... ✨"],
        "thinking": ["Consultando a los espíritus... 🔮"],
        "sleeping": ["Zzz... kon..."],
        "wake": ["¡Kon! ¿Ya amaneció?"],
        "eating": ["¡Inari-zushi! Mi favorito 🍣"],
        "full": ["Los zorros también tenemos límite 🦊"],
        "error": ["Un mal espíritu en el código... 💦"],
        "celebrate": ["¡Bendición completada! 🎉"],
        "sad": ["Mi fuego espiritual está bajo... 💧"],
        "hungry": ["¿Tienes tofu frito? 🥺"],
        "tired": ["Necesito meditar (dormir) un rato..."],
        "broke": ["Las ofrendas se acabaron... 💸"],
        "chat": ["Los espíritus responderán cuando MEKA Core despierte 🔮"]
      }
    }
  }
};
