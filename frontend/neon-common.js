const NeonCommon = (() => {
    let authToken = localStorage.getItem("neonArenaToken") || "";
    let player = null;
    let wallet = null;
    let chatTimer = null;
    let onlineTimer = null;
    let options = {};

    function authHeaders() {
        return {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + authToken
        };
    }

    function visitorId() {
        let id = localStorage.getItem("neonArenaVisitorId");
        if (!id) {
            id = "visitante-" + Date.now() + "-" + Math.random().toString(16).slice(2);
            localStorage.setItem("neonArenaVisitorId", id);
        }
        return id;
    }

    function setText(id, value) {
        const element = document.getElementById(id);
        if (element) element.innerText = value;
    }

    function setValue(id, value) {
        const element = document.getElementById(id);
        if (element) element.value = value;
    }

    function getValue(id) {
        const element = document.getElementById(id);
        return element ? element.value.trim() : "";
    }

    function show(id, display = "block") {
        const element = document.getElementById(id);
        if (element) element.style.display = display;
    }

    function hide(id) {
        const element = document.getElementById(id);
        if (element) element.style.display = "none";
    }

    function renderTop() {
        const name = player ? player.apelido : "Visitante";
        setText("topPlayerName", name);
        setText("topUserName", name);
        setText("topWallet", wallet ? wallet.saldo + " Moedas" : "0 Moedas");

        const account = document.getElementById("topAccount");
        if (account) account.classList.toggle("logged", Boolean(player));
    }

    async function loadProfile() {
        if (!authToken) {
            player = null;
            wallet = null;
            renderTop();
            return null;
        }

        const response = await fetch("/api/auth/me", {
            headers: authHeaders()
        }).catch(() => null);

        if (!response) return null;
        const data = await response.json();

        if (!data.sucesso) {
            authToken = "";
            player = null;
            wallet = null;
            localStorage.removeItem("neonArenaToken");
            renderTop();
            return null;
        }

        player = data.player;
        wallet = data.wallet;
        localStorage.setItem("neonArenaNome", player.apelido);
        renderTop();
        window.dispatchEvent(new CustomEvent("neon:profile", { detail: data }));
        return data;
    }

    async function heartbeat() {
        const response = await fetch("/api/online/heartbeat", {
            method: "POST",
            headers: authToken ? authHeaders() : { "Content-Type": "application/json" },
            body: JSON.stringify({
                visitor_id: visitorId(),
                nome: localStorage.getItem("neonArenaNome") || "Visitante"
            })
        }).catch(() => null);

        if (!response) return;
        const data = await response.json();
        setText("onlinePlayers", data.online || 0);
        setText("homeOnlinePlayers", data.online || 0);
    }

    function openAuthModal() {
        if (!document.getElementById("authModal")) {
            const current = window.location.pathname.split("/").pop() || "index.html";
            window.location.href = "index.html?login=1&next=" + encodeURIComponent(current);
            return;
        }
        setValue("loginApelido", localStorage.getItem("neonArenaNome") || "");
        show("authModal", "flex");
    }

    function closeAuthModal() {
        hide("authModal");
    }

    async function cadastrarConta() {
        const apelido = getValue("loginApelido");
        const usuario = getValue("loginUsuario");
        const senha = getValue("loginSenha");

        const response = await fetch("/api/auth/cadastrar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ apelido, usuario, senha, email: "" })
        });
        const data = await response.json();

        if (!data.sucesso) {
            alert(data.mensagem);
            return;
        }

        salvarSessao(data);
    }

    async function entrarConta() {
        const usuario = getValue("loginUsuario");
        const senha = getValue("loginSenha");

        const response = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ usuario, senha })
        });
        const data = await response.json();

        if (!data.sucesso) {
            alert(data.mensagem);
            return;
        }

        salvarSessao(data);
    }

    async function salvarSessao(data) {
        authToken = data.token;
        player = data.player;
        localStorage.setItem("neonArenaToken", authToken);
        localStorage.setItem("neonArenaNome", player.apelido);
        setValue("loginSenha", "");
        closeAuthModal();
        await loadProfile();

        const next = new URLSearchParams(window.location.search).get("next");
        if (options.redirectAfterLogin) {
            window.location.href = options.redirectAfterLogin;
            return;
        }
        if (next) {
            window.location.href = next;
        }
    }

    async function sairConta() {
        if (authToken) {
            await fetch("/api/auth/logout", {
                method: "POST",
                headers: authHeaders()
            }).catch(() => {});
        }
        authToken = "";
        player = null;
        wallet = null;
        localStorage.removeItem("neonArenaToken");
        renderTop();
        if (options.requireAuth) {
            window.location.href = "index.html?login=1";
        }
    }

    function jogarAirHockey() {
        if (authToken) {
            window.location.href = "air-hockey.html";
            return;
        }
        options.redirectAfterLogin = "air-hockey.html";
        openAuthModal();
    }

    async function receberBonusMoedas() {
        if (!authToken) {
            openAuthModal();
            return;
        }

        const response = await fetch("/api/carteira/bonus", {
            method: "POST",
            headers: authHeaders()
        });
        const data = await response.json();

        if (!data.sucesso) {
            alert(data.mensagem);
            return;
        }

        await loadProfile();
        alert("Moedas adicionadas.");
    }

    async function carregarChat() {
        const list = document.getElementById("chatMessages");
        if (!list) return;

        const response = await fetch("/api/chat").catch(() => null);
        if (!response) return;
        const data = await response.json();

        if (!data.sucesso || !data.mensagens.length) {
            list.innerHTML = "<p class=\"empty-history\">Nenhuma mensagem ainda.</p>";
            return;
        }

        list.innerHTML = data.mensagens.map((msg) => `
            <div class="chat-message">
                <div><strong>${escapeHtml(msg.nome)}</strong><span>${escapeHtml(msg.horario)}</span></div>
                <p>${escapeHtml(msg.mensagem)}</p>
            </div>
        `).join("");
        list.scrollTop = list.scrollHeight;
    }

    function abrirChat() {
        show("chatPanel", "flex");
        carregarChat();
        if (!chatTimer) chatTimer = setInterval(carregarChat, 2500);
    }

    function fecharChat() {
        hide("chatPanel");
        if (chatTimer) {
            clearInterval(chatTimer);
            chatTimer = null;
        }
    }

    async function enviarChat(event) {
        event.preventDefault();
        if (!authToken) {
            openAuthModal();
            return;
        }

        const input = document.getElementById("chatInput");
        const mensagem = input.value.trim();
        if (!mensagem) return;

        const response = await fetch("/api/chat", {
            method: "POST",
            headers: authHeaders(),
            body: JSON.stringify({ mensagem })
        });
        const data = await response.json();

        if (!data.sucesso) {
            alert(data.mensagem);
            return;
        }

        input.value = "";
        await carregarChat();
    }

    function escapeHtml(value) {
        return String(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll("\"", "&quot;")
            .replaceAll("'", "&#039;");
    }

    async function init(initOptions = {}) {
        options = initOptions;
        await loadProfile();
        await heartbeat();
        if (onlineTimer) clearInterval(onlineTimer);
        onlineTimer = setInterval(heartbeat, 5000);

        const params = new URLSearchParams(window.location.search);
        if (params.get("login") === "1") openAuthModal();

        if (options.requireAuth && !authToken) {
            window.location.href = "index.html?login=1&next=" + encodeURIComponent(window.location.pathname.split("/").pop());
        }
    }

    return {
        init,
        authHeaders,
        get token() { return authToken; },
        get player() { return player; },
        get wallet() { return wallet; },
        openAuthModal,
        closeAuthModal,
        cadastrarConta,
        entrarConta,
        sairConta,
        jogarAirHockey,
        receberBonusMoedas,
        abrirChat,
        fecharChat,
        enviarChat,
        carregarChat
    };
})();
