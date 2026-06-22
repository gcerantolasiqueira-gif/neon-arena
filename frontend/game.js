const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");

const WIDTH = canvas.width;
const HEIGHT = canvas.height;

const PLAYER_RADIUS = 34;
const PUCK_RADIUS = 19;
const PLAYER_SPEED = 8.5;
const ONLINE_PREDICTION_SPEED = 10.2;
const ONLINE_REMOTE_SMOOTHING = 0.28;
const ONLINE_TELEPORT_DISTANCE = 160;
const FRICTION = 0.996;
const HIT_POWER = 14;
const MAX_PUCK_SPEED = 24;
const GOAL_HEIGHT = 190;
const WIN_SCORE = 7;

const params = new URLSearchParams(window.location.search);
const sala = params.get("sala") || "LOCAL";
const modo = params.get("modo") || "local";
const nivel = params.get("nivel") || "medio";
const jogadorOnline = Number(params.get("jogador") || "1");
const isOnline = modo === "online";
const meuNome = (localStorage.getItem("neonArenaNome") || "NeonPlayer").slice(0, 18);
const authToken = localStorage.getItem("neonArenaToken") || "";

let scoreP1 = 0;
let scoreP2 = 0;
let nomeP1 = modo === "bot" ? meuNome : "Jogador 1";
let nomeP2 = modo === "bot" ? "Robô" : "Jogador 2";
let touchesP1 = 0;
let touchesP2 = 0;
let shotsP1 = 0;
let shotsP2 = 0;
let gameOver = false;
let pausedAfterGoal = false;
let countdown = 3;
let countdownActive = true;
let countdownText = "3";
let goalFlash = 0;
let goalMessageTimer = 0;
let goalMessageText = "";
let arenaShake = 0;
let particles = [];
let audioEnabled = true;
let musicEnabled = true;
let lastHitSoundTime = 0;
let lastWallSoundTime = 0;
let victorySoundPlayed = false;
let historicoSalvo = false;
let resultadoFinalVisivel = false;
let socket = null;
let lastOnlineEventId = 0;
let apostaAtual = 0;
let matchUidAtual = "";
let intervaloInputOnline = null;
let ultimoInputOnline = "";
let ultimoEnvioInputOnline = 0;
let alvoOnlineP1 = null;
let alvoOnlineP2 = null;

const sounds = {
    hit: new Audio("sounds/hit.wav"),
    wall: new Audio("sounds/wall.wav"),
    goal: new Audio("sounds/goal.wav"),
    victory: new Audio("sounds/victory.wav"),
    music: new Audio("sounds/music.wav")
};

sounds.hit.volume = 0.45;
sounds.wall.volume = 0.35;
sounds.goal.volume = 0.65;
sounds.victory.volume = 0.75;
sounds.music.volume = 0.18;
sounds.music.loop = true;

let p1 = {
    x: 170,
    y: HEIGHT / 2,
    lastX: 170,
    lastY: HEIGHT / 2,
    color: "#ff416d"
};

let p2 = {
    x: WIDTH - 170,
    y: HEIGHT / 2,
    lastX: WIDTH - 170,
    lastY: HEIGHT / 2,
    color: "#00eaff"
};

let puck = {
    x: WIDTH / 2,
    y: HEIGHT / 2,
    vx: 0,
    vy: 0,
    color: "#ffffff"
};

let keys = {
    w: false,
    a: false,
    s: false,
    d: false,
    ArrowUp: false,
    ArrowDown: false,
    ArrowLeft: false,
    ArrowRight: false
};

document.getElementById("roomCode").innerText = sala;
atualizarBotaoAudio();
atualizarBotaoMusica();
atualizarInformacoesDaPartida();
atualizarNomesJogadores();

function atualizarInformacoesDaPartida() {
    const matchMode = document.getElementById("matchMode");
    const connectionStatus = document.getElementById("connectionStatus");
    const controlsText = document.getElementById("controlsText");

    if (modo === "bot") {
        matchMode.innerText = "Treino " + nivel;
        connectionStatus.innerText = "Local";
        controlsText.innerText = "Controle: W A S D";
        return;
    }

    if (isOnline) {
        matchMode.innerText = "Online";
        connectionStatus.innerText = "Conectando";
        controlsText.innerText = jogadorOnline === 1
            ? "Você é o Jogador 1: use W A S D ou as setas"
            : "Você é o Jogador 2: use W A S D ou as setas";
        return;
    }

    matchMode.innerText = "1x1";
    connectionStatus.innerText = "Local";
    controlsText.innerText = "Jogador 1: W A S D | Jogador 2: Setas do teclado";
}

function atualizarStatusConexao(texto) {
    const connectionStatus = document.getElementById("connectionStatus");
    if (connectionStatus) connectionStatus.innerText = texto;
}

function atualizarNomesJogadores() {
    if (!isOnline && modo !== "bot") {
        nomeP1 = "Jogador 1";
        nomeP2 = "Jogador 2";
    }

    if (modo === "bot") {
        nomeP1 = meuNome;
        nomeP2 = "Robô";
    }

    document.getElementById("playerNameP1").innerText = nomeP1;
    document.getElementById("playerNameP2").innerText = nomeP2;
}

function voltarLobby() {
    window.location.href = "air-hockey.html";
}

function alternarAudio() {
    audioEnabled = !audioEnabled;
    atualizarBotaoAudio();
}

function atualizarBotaoAudio() {
    const button = document.getElementById("audioButton");
    if (!button) return;

    button.innerText = audioEnabled ? "Som: ligado" : "Som: desligado";
    button.classList.toggle("muted", !audioEnabled);
}

function alternarMusica() {
    musicEnabled = !musicEnabled;
    atualizarBotaoMusica();

    if (!musicEnabled) {
        sounds.music.pause();
    } else {
        iniciarMusica();
    }
}

function atualizarBotaoMusica() {
    const button = document.getElementById("musicButton");
    if (!button) return;

    button.innerText = musicEnabled ? "Música: ligada" : "Música: desligada";
    button.classList.toggle("muted", !musicEnabled);
}

function tocarSom(nome) {
    if (!audioEnabled || !sounds[nome]) return;

    sounds[nome].currentTime = 0;
    sounds[nome].play().catch(() => {});
}

function iniciarMusica() {
    if (!musicEnabled || gameOver) return;
    sounds.music.play().catch(() => {});
}

function tocarSomHit() {
    const agora = performance.now();
    if (agora - lastHitSoundTime < 70) return;

    lastHitSoundTime = agora;
    tocarSom("hit");
}

function tocarSomParede() {
    const agora = performance.now();
    if (agora - lastWallSoundTime < 90) return;

    lastWallSoundTime = agora;
    tocarSom("wall");
}

function criarParticulas(x, y, cor, quantidade, forca = 6) {
    for (let i = 0; i < quantidade; i++) {
        const angulo = Math.random() * Math.PI * 2;
        const velocidade = Math.random() * forca + 1.5;

        particles.push({
            x,
            y,
            vx: Math.cos(angulo) * velocidade,
            vy: Math.sin(angulo) * velocidade,
            radius: Math.random() * 4 + 2,
            life: Math.random() * 28 + 22,
            maxLife: 50,
            color: cor
        });
    }
}

function atualizarParticulas() {
    particles = particles.filter((particle) => particle.life > 0);

    for (const particle of particles) {
        particle.x += particle.vx;
        particle.y += particle.vy;
        particle.vx *= 0.96;
        particle.vy *= 0.96;
        particle.life--;
    }
}

function desenharParticulas() {
    for (const particle of particles) {
        const alpha = Math.max(particle.life / particle.maxLife, 0);

        ctx.beginPath();
        ctx.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2);
        ctx.fillStyle = converterCorParaRgba(particle.color, alpha);
        ctx.shadowColor = particle.color;
        ctx.shadowBlur = 16;
        ctx.fill();
    }

    ctx.shadowBlur = 0;
}

function converterCorParaRgba(hex, alpha) {
    const cleanHex = hex.replace("#", "");
    const r = parseInt(cleanHex.substring(0, 2), 16);
    const g = parseInt(cleanHex.substring(2, 4), 16);
    const b = parseInt(cleanHex.substring(4, 6), 16);

    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function limitarJogador(player, lado) {
    player.y = Math.max(PLAYER_RADIUS, Math.min(HEIGHT - PLAYER_RADIUS, player.y));

    if (lado === "left") {
        player.x = Math.max(PLAYER_RADIUS, Math.min(WIDTH / 2 - PLAYER_RADIUS, player.x));
    } else {
        player.x = Math.max(WIDTH / 2 + PLAYER_RADIUS, Math.min(WIDTH - PLAYER_RADIUS, player.x));
    }
}

document.addEventListener("keydown", function(event) {
    if (event.key in keys) {
        iniciarMusica();
        keys[event.key] = true;
        enviarInputOnline();
    }
});

document.addEventListener("keyup", function(event) {
    if (event.key in keys) {
        keys[event.key] = false;
        enviarInputOnline();
    }
});

document.addEventListener("pointerdown", iniciarMusica);

function moverJogadores() {
    if (isOnline) {
        moverJogadorOnlinePrevisto();
        suavizarJogadorOnlineRemoto();
        return;
    }

    if (gameOver || pausedAfterGoal || countdownActive) return;

    p1.lastX = p1.x;
    p1.lastY = p1.y;
    p2.lastX = p2.x;
    p2.lastY = p2.y;

    if (keys.w) p1.y -= PLAYER_SPEED;
    if (keys.s) p1.y += PLAYER_SPEED;
    if (keys.a) p1.x -= PLAYER_SPEED;
    if (keys.d) p1.x += PLAYER_SPEED;

    if (modo === "bot") {
        moverRobo();
    } else {
        if (keys.ArrowUp) p2.y -= PLAYER_SPEED;
        if (keys.ArrowDown) p2.y += PLAYER_SPEED;
        if (keys.ArrowLeft) p2.x -= PLAYER_SPEED;
        if (keys.ArrowRight) p2.x += PLAYER_SPEED;
    }

    limitarJogador(p1, "left");
    limitarJogador(p2, "right");
}

function suavizarJogadorOnlineRemoto() {
    const alvo = jogadorOnline === 1 ? alvoOnlineP2 : alvoOnlineP1;
    const player = jogadorOnline === 1 ? p2 : p1;

    if (!alvo) return;

    const distancia = Math.hypot(alvo.x - player.x, alvo.y - player.y);
    if (distancia > ONLINE_TELEPORT_DISTANCE) {
        player.x = alvo.x;
        player.y = alvo.y;
        player.lastX = alvo.lastX ?? alvo.x;
        player.lastY = alvo.lastY ?? alvo.y;
        return;
    }

    player.lastX = player.x;
    player.lastY = player.y;
    player.x += (alvo.x - player.x) * ONLINE_REMOTE_SMOOTHING;
    player.y += (alvo.y - player.y) * ONLINE_REMOTE_SMOOTHING;
}

function moverJogadorOnlinePrevisto() {
    if (gameOver || pausedAfterGoal || countdownActive) return;

    const player = jogadorOnline === 1 ? p1 : p2;
    const lado = jogadorOnline === 1 ? "left" : "right";
    const movimento = obterMovimentoCompartilhado();

    player.lastX = player.x;
    player.lastY = player.y;

    if (movimento.x === 0 && movimento.y === 0) return;

    const tamanho = Math.hypot(movimento.x, movimento.y);

    player.x += movimento.x / tamanho * ONLINE_PREDICTION_SPEED;
    player.y += movimento.y / tamanho * ONLINE_PREDICTION_SPEED;

    limitarJogador(player, lado);
}

function obterMovimentoCompartilhado() {
    let x = 0;
    let y = 0;

    if (keys.w || keys.ArrowUp) y -= 1;
    if (keys.s || keys.ArrowDown) y += 1;
    if (keys.a || keys.ArrowLeft) x -= 1;
    if (keys.d || keys.ArrowRight) x += 1;

    return { x, y };
}

function moverRobo() {
    let velocidadeRobo = 5.2;
    let erro = 32;
    let agressividade = 80;

    if (nivel === "facil") {
        velocidadeRobo = 3.5;
        erro = 90;
        agressividade = 130;
    }

    if (nivel === "medio") {
        velocidadeRobo = 5.2;
        erro = 42;
        agressividade = 90;
    }

    if (nivel === "dificil") {
        velocidadeRobo = 6.8;
        erro = 18;
        agressividade = 55;
    }

    if (nivel === "insano") {
        velocidadeRobo = 8.1;
        erro = 5;
        agressividade = 25;
    }

    let alvoX = WIDTH - 170;
    let alvoY = HEIGHT / 2;
    const discoVindo = puck.vx > 0;

    if (discoVindo || puck.x > WIDTH / 2) {
        alvoY = puck.y + Math.sin(Date.now() / 220) * erro;
        alvoX = Math.max(WIDTH / 2 + PLAYER_RADIUS, puck.x - agressividade);
    } else {
        alvoY = HEIGHT / 2 + Math.sin(Date.now() / 500) * 60;
        alvoX = WIDTH - 180;
    }

    const dx = alvoX - p2.x;
    const dy = alvoY - p2.y;

    if (Math.abs(dx) > 3) {
        p2.x += Math.sign(dx) * Math.min(Math.abs(dx), velocidadeRobo);
    }

    if (Math.abs(dy) > 3) {
        p2.y += Math.sign(dy) * Math.min(Math.abs(dy), velocidadeRobo);
    }
}

function limitarVelocidadeDisco() {
    const velocidade = Math.hypot(puck.vx, puck.vy);

    if (velocidade > MAX_PUCK_SPEED) {
        const fator = MAX_PUCK_SPEED / velocidade;
        puck.vx *= fator;
        puck.vy *= fator;
    }
}

function colisaoJogadorDisco(player, nome) {
    const dx = puck.x - player.x;
    const dy = puck.y - player.y;
    const dist = Math.hypot(dx, dy);
    const minDist = PLAYER_RADIUS + PUCK_RADIUS;

    if (dist < minDist && dist > 0) {
        const nx = dx / dist;
        const ny = dy / dist;

        puck.x = player.x + nx * minDist;
        puck.y = player.y + ny * minDist;

        const playerVx = player.x - player.lastX;
        const playerVy = player.y - player.lastY;
        const playerSpeed = Math.hypot(playerVx, playerVy);
        const velocidadeAtual = Math.hypot(puck.vx, puck.vy);
        const novaVelocidade = Math.max(HIT_POWER + playerSpeed * 0.8, velocidadeAtual + 2.5);

        puck.vx = nx * novaVelocidade + playerVx * 0.45;
        puck.vy = ny * novaVelocidade + playerVy * 0.45;

        if (nome === "p1") {
            touchesP1++;
            if (puck.vx > 0) shotsP1++;
            criarParticulas(puck.x, puck.y, "#ff416d", 12, 5);
        } else {
            touchesP2++;
            if (puck.vx < 0) shotsP2++;
            criarParticulas(puck.x, puck.y, "#00eaff", 12, 5);
        }

        tocarSomParede();
        limitarVelocidadeDisco();
    }
}

function atualizarDisco() {
    if (gameOver || pausedAfterGoal || countdownActive || isOnline) return;

    puck.x += puck.vx;
    puck.y += puck.vy;
    puck.vx *= FRICTION;
    puck.vy *= FRICTION;

    if (Math.abs(puck.vx) < 0.03) puck.vx = 0;
    if (Math.abs(puck.vy) < 0.03) puck.vy = 0;

    const goalTop = HEIGHT / 2 - GOAL_HEIGHT / 2;
    const goalBottom = HEIGHT / 2 + GOAL_HEIGHT / 2;
    const dentroDoGol = puck.y > goalTop && puck.y < goalBottom;

    if (puck.x - PUCK_RADIUS <= 0) {
        if (dentroDoGol) {
            marcarGol("p2");
            return;
        }

        puck.x = PUCK_RADIUS;
        puck.vx *= -1;
        criarParticulas(puck.x, puck.y, "#ffffff", 7, 3);
        tocarSomParede();
    }

    if (puck.x + PUCK_RADIUS >= WIDTH) {
        if (dentroDoGol) {
            marcarGol("p1");
            return;
        }

        puck.x = WIDTH - PUCK_RADIUS;
        puck.vx *= -1;
        criarParticulas(puck.x, puck.y, "#ffffff", 7, 3);
        tocarSomParede();
    }

    if (puck.y - PUCK_RADIUS <= 0) {
        puck.y = PUCK_RADIUS;
        puck.vy *= -1;
        criarParticulas(puck.x, puck.y, "#ffffff", 7, 3);
        tocarSomParede();
    }

    if (puck.y + PUCK_RADIUS >= HEIGHT) {
        puck.y = HEIGHT - PUCK_RADIUS;
        puck.vy *= -1;
        criarParticulas(puck.x, puck.y, "#ffffff", 7, 3);
        tocarSomHit();
    }

    colisaoJogadorDisco(p1, "p1");
    colisaoJogadorDisco(p2, "p2");
}

function iniciarContagem() {
    countdown = 3;
    countdownText = "3";
    countdownActive = true;

    let intervalo = setInterval(() => {
        if (isOnline) {
            clearInterval(intervalo);
            return;
        }

        countdown--;

        if (countdown > 0) {
            countdownText = String(countdown);
        } else if (countdown === 0) {
            countdownText = "GO!";
        } else {
            clearInterval(intervalo);
            countdownActive = false;
            iniciarDisco();
        }
    }, 850);
}

function iniciarDisco() {
    puck.vx = Math.random() > 0.5 ? 8 : -8;
    puck.vy = Math.random() > 0.5 ? 4 : -4;
}

function resetarJogo() {
    if (isOnline) {
        ocultarResultadoFinal();
        enviarResetOnline();
        return;
    }

    scoreP1 = 0;
    scoreP2 = 0;
    touchesP1 = 0;
    touchesP2 = 0;
    shotsP1 = 0;
    shotsP2 = 0;
    gameOver = false;
    historicoSalvo = false;
    resultadoFinalVisivel = false;
    matchUidAtual = "";
    pausedAfterGoal = false;
    goalFlash = 0;
    goalMessageTimer = 0;
    particles = [];
    arenaShake = 0;
    victorySoundPlayed = false;

    resetarPosicoes(false);
    atualizarPlacar();
    ocultarResultadoFinal();
    iniciarContagem();
}

function resetarPosicoes(iniciarDepois = true, direcao = 1) {
    p1.x = 170;
    p1.y = HEIGHT / 2;
    p1.lastX = p1.x;
    p1.lastY = p1.y;
    p2.x = WIDTH - 170;
    p2.y = HEIGHT / 2;
    p2.lastX = p2.x;
    p2.lastY = p2.y;
    puck.x = WIDTH / 2;
    puck.y = HEIGHT / 2;
    puck.vx = 0;
    puck.vy = 0;

    if (iniciarDepois && !gameOver) {
        pausedAfterGoal = true;

        setTimeout(() => {
            pausedAfterGoal = false;
            puck.vx = 8 * direcao;
            puck.vy = Math.random() > 0.5 ? 4 : -4;
        }, 900);
    }
}

function atualizarPlacar() {
    document.getElementById("scoreP1").innerText = scoreP1;
    document.getElementById("scoreP2").innerText = scoreP2;
}

function marcarGol(jogador) {
    if (jogador === "p1") {
        scoreP1++;
        goalMessageText = "GOOOOL DE " + nomeP1.toUpperCase() + "!";
        criarParticulas(WIDTH - 28, HEIGHT / 2, "#00eaff", 52, 9);
        resetarPosicoes(true, 1);
    } else {
        scoreP2++;
        goalMessageText = "GOOOOL DE " + nomeP2.toUpperCase() + "!";
        criarParticulas(28, HEIGHT / 2, "#ff416d", 52, 9);
        resetarPosicoes(true, -1);
    }

    goalFlash = 24;
    goalMessageTimer = 58;
    arenaShake = 14;

    tocarSom("goal");
    atualizarPlacar();
    verificarVitoria();
}

function verificarVitoria() {
    if (scoreP1 >= WIN_SCORE || scoreP2 >= WIN_SCORE) {
        gameOver = true;
        puck.vx = 0;
        puck.vy = 0;
        sounds.music.pause();

        if (!victorySoundPlayed) {
            victorySoundPlayed = true;
            setTimeout(() => tocarSom("victory"), 250);
        }

        salvarHistoricoPartida();
    }
}

function conectarOnline() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    socket = new WebSocket(`${protocol}//${window.location.host}/ws/air-hockey/${sala}/${jogadorOnline}`);

    socket.addEventListener("open", () => {
        atualizarStatusConexao("Online");
        socket.send(JSON.stringify({
            type: "player_info",
            nome: meuNome,
            token: authToken
        }));
        if (intervaloInputOnline) {
            clearInterval(intervaloInputOnline);
        }
        intervaloInputOnline = setInterval(enviarInputOnline, 1000 / 30);
    });

    socket.addEventListener("message", (event) => {
        const data = JSON.parse(event.data);

        if (data.type === "state") {
            aplicarEstadoOnline(data.game, data.room);
        }
    });

    socket.addEventListener("close", () => {
        atualizarStatusConexao("Desconectado");
        if (intervaloInputOnline) {
            clearInterval(intervaloInputOnline);
            intervaloInputOnline = null;
        }
    });
}

function enviarInputOnline() {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

    const movimento = obterMovimentoCompartilhado();
    const sharedKeys = {
        up: movimento.y < 0,
        down: movimento.y > 0,
        left: movimento.x < 0,
        right: movimento.x > 0
    };

    const assinatura = JSON.stringify(sharedKeys);
    const agora = performance.now();
    if (assinatura === ultimoInputOnline && agora - ultimoEnvioInputOnline < 250) {
        return;
    }

    ultimoInputOnline = assinatura;
    ultimoEnvioInputOnline = agora;

    socket.send(JSON.stringify({
        type: "input",
        keys: sharedKeys
    }));
}

function enviarResetOnline() {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

    historicoSalvo = false;
    resultadoFinalVisivel = false;
    victorySoundPlayed = false;
    ocultarResultadoFinal();

    socket.send(JSON.stringify({
        type: "reset"
    }));
}

function aplicarEstadoOnline(game, room) {
    const estavaFinalizado = gameOver;

    atualizarJogadoresOnline(game);
    puck.x = game.puck.x;
    puck.y = game.puck.y;
    puck.vx = game.puck.vx;
    puck.vy = game.puck.vy;

    scoreP1 = game.score.p1;
    scoreP2 = game.score.p2;
    touchesP1 = game.stats.p1.touches;
    touchesP2 = game.stats.p2.touches;
    shotsP1 = game.stats.p1.shots;
    shotsP2 = game.stats.p2.shots;

    if (room.players) {
        nomeP1 = room.players.p1 || "Jogador 1";
        nomeP2 = room.players.p2 || "Jogador 2";
        atualizarNomesJogadores();
    }

    apostaAtual = room.aposta || 0;

    atualizarPlacar();

    gameOver = game.status === "finished";
    if (!gameOver) {
        resultadoFinalVisivel = false;
        ocultarResultadoFinal();
    }

    countdownActive = game.status === "countdown" || room.status === "aguardando";
    if (room.status === "aguardando_login") {
        countdownText = "LOGIN";
        countdownActive = true;
    } else if (room.status === "saldo_insuficiente") {
        countdownText = "SEM SALDO";
        countdownActive = true;
    } else {
        countdownText = room.status === "aguardando" ? "AGUARDANDO" : (game.countdown > 0 ? String(game.countdown) : "GO!");
    }

    if (game.event && game.event.id !== lastOnlineEventId) {
        lastOnlineEventId = game.event.id;
        if (game.event.type === "victory") {
            matchUidAtual = `${sala}-${game.event.id}-${scoreP1}-${scoreP2}`;
        }
        executarEventoOnline(game.event);
    }

    if (gameOver && !estavaFinalizado) {
        salvarHistoricoPartida();
    }
}

function atualizarJogadoresOnline(game) {
    const estadoP1 = { ...game.p1, color: "#ff416d" };
    const estadoP2 = { ...game.p2, color: "#00eaff" };

    if (!alvoOnlineP1 || !alvoOnlineP2) {
        p1 = estadoP1;
        p2 = estadoP2;
        alvoOnlineP1 = { ...estadoP1 };
        alvoOnlineP2 = { ...estadoP2 };
        return;
    }

    alvoOnlineP1 = estadoP1;
    alvoOnlineP2 = estadoP2;

    const estadoLocal = jogadorOnline === 1 ? estadoP1 : estadoP2;
    const jogadorLocal = jogadorOnline === 1 ? p1 : p2;
    const movimento = obterMovimentoCompartilhado();

    // A predicao local evita saltos visiveis enquanto a tecla esta pressionada.
    if (movimento.x === 0 && movimento.y === 0) {
        const distancia = Math.hypot(estadoLocal.x - jogadorLocal.x, estadoLocal.y - jogadorLocal.y);
        if (distancia > ONLINE_TELEPORT_DISTANCE) {
            jogadorLocal.x = estadoLocal.x;
            jogadorLocal.y = estadoLocal.y;
            jogadorLocal.lastX = estadoLocal.lastX;
            jogadorLocal.lastY = estadoLocal.lastY;
        } else {
            jogadorLocal.x += (estadoLocal.x - jogadorLocal.x) * 0.18;
            jogadorLocal.y += (estadoLocal.y - jogadorLocal.y) * 0.18;
        }
    }
}

function executarEventoOnline(event) {
    if (event.type === "hit") {
        criarParticulas(event.x, event.y, event.color, 12, 5);
        if (event.color === "#ffffff") {
            tocarSomParede();
        } else {
            tocarSomHit();
        }
    }

    if (event.type === "goal") {
        goalMessageText = event.message;
        goalMessageTimer = 58;
        goalFlash = 24;
        arenaShake = 14;
        criarParticulas(event.x, event.y, event.color, 52, 9);
        tocarSom("goal");
    }

    if (event.type === "victory") {
        if (!victorySoundPlayed) {
            victorySoundPlayed = true;
            setTimeout(() => tocarSom("victory"), 250);
        }
    }
}

function desenharCampo() {
    ctx.clearRect(0, 0, WIDTH, HEIGHT);
    ctx.save();

    if (arenaShake > 0) {
        const shakeX = (Math.random() - 0.5) * arenaShake;
        const shakeY = (Math.random() - 0.5) * arenaShake;
        ctx.translate(shakeX, shakeY);
        arenaShake *= 0.84;
        if (arenaShake < 0.6) arenaShake = 0;
    }

    ctx.fillStyle = "#101827";
    ctx.fillRect(0, 0, WIDTH, HEIGHT);

    ctx.strokeStyle = "rgba(0,234,255,0.08)";
    ctx.lineWidth = 1;

    for (let x = 60; x < WIDTH; x += 60) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, HEIGHT);
        ctx.stroke();
    }

    for (let y = 60; y < HEIGHT; y += 60) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(WIDTH, y);
        ctx.stroke();
    }

    if (goalFlash > 0) {
        ctx.fillStyle = "rgba(255,255,255,0.14)";
        ctx.fillRect(0, 0, WIDTH, HEIGHT);
        goalFlash--;
    }

    ctx.strokeStyle = "rgba(255,255,255,0.92)";
    ctx.lineWidth = 4;
    ctx.strokeRect(2, 2, WIDTH - 4, HEIGHT - 4);

    ctx.strokeStyle = "rgba(255,255,255,0.35)";
    ctx.lineWidth = 4;

    ctx.beginPath();
    ctx.moveTo(WIDTH / 2, 0);
    ctx.lineTo(WIDTH / 2, HEIGHT);
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(WIDTH / 2, HEIGHT / 2, 80, 0, Math.PI * 2);
    ctx.stroke();

    ctx.fillStyle = "#ff416d";
    ctx.shadowColor = "#ff416d";
    ctx.shadowBlur = 25;
    ctx.fillRect(0, HEIGHT / 2 - GOAL_HEIGHT / 2, 18, GOAL_HEIGHT);

    ctx.fillStyle = "#00eaff";
    ctx.shadowColor = "#00eaff";
    ctx.shadowBlur = 25;
    ctx.fillRect(WIDTH - 18, HEIGHT / 2 - GOAL_HEIGHT / 2, 18, GOAL_HEIGHT);

    ctx.shadowBlur = 0;
}

function desenharJogador(player) {
    ctx.beginPath();
    ctx.arc(player.x, player.y, PLAYER_RADIUS, 0, Math.PI * 2);
    ctx.fillStyle = player.color;
    ctx.shadowColor = player.color;
    ctx.shadowBlur = 25;
    ctx.fill();

    ctx.shadowBlur = 0;
    ctx.strokeStyle = "white";
    ctx.lineWidth = 4;
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(player.x, player.y, 9, 0, Math.PI * 2);
    ctx.fillStyle = "white";
    ctx.fill();
}

function desenharDisco() {
    ctx.beginPath();
    ctx.arc(puck.x, puck.y, PUCK_RADIUS, 0, Math.PI * 2);
    ctx.fillStyle = puck.color;
    ctx.shadowColor = "#ffffff";
    ctx.shadowBlur = 22;
    ctx.fill();

    ctx.shadowBlur = 0;
    ctx.strokeStyle = "#00eaff";
    ctx.lineWidth = 3;
    ctx.stroke();
}

function desenharContagem() {
    if (!countdownActive) return;

    ctx.fillStyle = "rgba(0,0,0,0.45)";
    ctx.fillRect(0, 0, WIDTH, HEIGHT);

    ctx.fillStyle = "white";
    ctx.font = countdownText === "AGUARDANDO" ? "bold 52px Arial" : "bold 90px Arial";
    ctx.textAlign = "center";
    ctx.fillText(countdownText, WIDTH / 2, HEIGHT / 2 + 30);
}

function desenharGolMensagem() {
    if (goalMessageTimer <= 0) return;

    ctx.fillStyle = "rgba(0,0,0,0.25)";
    ctx.fillRect(0, 0, WIDTH, HEIGHT);

    ctx.fillStyle = "white";
    ctx.font = "bold 58px Arial";
    ctx.textAlign = "center";
    ctx.fillText(goalMessageText, WIDTH / 2, HEIGHT / 2 + 20);

    goalMessageTimer--;
}

function calcularPrecisao(gols, chutes) {
    if (chutes === 0) return 0;
    return Math.round((gols / chutes) * 100);
}

function desenharMensagemFinal() {
    if (!gameOver) return;

    ctx.fillStyle = "rgba(0,0,0,0.72)";
    ctx.fillRect(0, 0, WIDTH, HEIGHT);

    let vencedor = scoreP1 > scoreP2 ? nomeP1 + " venceu!" : nomeP2 + " venceu!";

    if (modo === "bot") {
        vencedor = scoreP1 > scoreP2 ? nomeP1 + " venceu o robô!" : "O robô venceu!";
    }

    if (isOnline) {
        vencedor = scoreP1 > scoreP2 ? nomeP1 + " venceu!" : nomeP2 + " venceu!";
    }

    ctx.fillStyle = "#00eaff";
    ctx.font = "bold 24px Arial";
    ctx.textAlign = "center";
    ctx.fillText("VENCEDOR DA ARENA", WIDTH / 2, HEIGHT / 2 - 130);

    ctx.fillStyle = "white";
    ctx.font = "bold 58px Arial";
    ctx.textAlign = "center";
    ctx.fillText(vencedor, WIDTH / 2, HEIGHT / 2 - 70);

    ctx.fillStyle = "#80ffcf";
    ctx.font = "bold 34px Arial";
    ctx.fillText(`${scoreP1} x ${scoreP2}`, WIDTH / 2, HEIGHT / 2);

    ctx.fillStyle = "#d8e0ff";
    ctx.font = "22px Arial";
    ctx.fillText("Escolha Novo jogo ou saia para o lobby.", WIDTH / 2, HEIGHT / 2 + 62);
}

function desenharModoTreino() {
    if (modo !== "bot") return;

    ctx.fillStyle = "rgba(255,255,255,0.85)";
    ctx.font = "bold 18px Arial";
    ctx.textAlign = "left";
    ctx.fillText("Modo treino contra robô - " + nivel.toUpperCase(), 25, HEIGHT - 25);
}

function salvarHistoricoPartida() {
    if (historicoSalvo) return;

    historicoSalvo = true;

    const vencedor = scoreP1 > scoreP2 ? nomeP1 : nomeP2;
    const partida = {
        data: new Date().toLocaleString("pt-BR"),
        modo,
        sala,
        match_uid: matchUidAtual || `${sala}-${Date.now()}-${scoreP1}-${scoreP2}`,
        jogador1: nomeP1,
        jogador2: nomeP2,
        placar: `${scoreP1} x ${scoreP2}`,
        vencedor
    };

    const historico = JSON.parse(localStorage.getItem("neonArenaHistorico") || "[]");
    historico.unshift(partida);
    localStorage.setItem("neonArenaHistorico", JSON.stringify(historico.slice(0, 20)));

    mostrarResultadoFinal();
    salvarPartidaNoServidor(partida);
}

function mostrarResultadoFinal() {
    if (resultadoFinalVisivel) return;

    resultadoFinalVisivel = true;

    const panel = document.getElementById("postMatchPanel");
    if (!panel) return;

    const vencedor = scoreP1 > scoreP2 ? nomeP1 : nomeP2;

    document.getElementById("postMatchTitle").innerText = "Vitória de " + vencedor;
    document.getElementById("postMatchSubtitle").innerText = `Placar final: ${scoreP1} x ${scoreP2}`;
    if (apostaAtual > 0) {
        document.getElementById("postMatchSubtitle").innerText =
            `Placar final: ${scoreP1} x ${scoreP2} | Partida valendo ${apostaAtual} Moedas Neon`;
    }
    document.getElementById("postNameP1").innerText = nomeP1;
    document.getElementById("postNameP2").innerText = nomeP2;
    document.getElementById("postScoreP1").innerText = scoreP1;
    document.getElementById("postScoreP2").innerText = scoreP2;

    panel.style.display = "block";
    panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function ocultarResultadoFinal() {
    const panel = document.getElementById("postMatchPanel");
    if (!panel) return;

    panel.style.display = "none";
}

async function salvarPartidaNoServidor(partida) {
    if (!authToken) return;

    const souP1 = partida.jogador1 === meuNome;
    const payload = {
        player_name: meuNome,
        opponent_name: souP1 ? partida.jogador2 : partida.jogador1,
        winner_name: partida.vencedor,
        score_player: souP1 ? scoreP1 : scoreP2,
        score_opponent: souP1 ? scoreP2 : scoreP1,
        mode: partida.modo,
        room_code: partida.sala,
        match_uid: partida.match_uid
    };

    await fetch("/api/partidas", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + authToken
        },
        body: JSON.stringify(payload)
    }).catch(() => {});
}

function loop() {
    moverJogadores();
    atualizarDisco();
    atualizarParticulas();

    desenharCampo();
    desenharJogador(p1);
    desenharJogador(p2);
    desenharDisco();
    desenharParticulas();
    desenharModoTreino();
    desenharGolMensagem();
    desenharContagem();
    desenharMensagemFinal();

    ctx.restore();
    requestAnimationFrame(loop);
}

if (isOnline) {
    countdownActive = true;
    countdownText = "AGUARDANDO";
    conectarOnline();
} else {
    atualizarPlacar();
    iniciarContagem();
}

loop();
