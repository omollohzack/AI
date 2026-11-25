const conversation = document.getElementById("conversation");
const composer = document.getElementById("composer");
const promptInput = document.getElementById("prompt");
const sendButton = document.getElementById("send-button");
const newChat = document.getElementById("new-chat");
const themeToggle = document.getElementById("theme-toggle");

function escapeHtml(value) {
  const element = document.createElement("div");
  element.textContent = value;
  return element.innerHTML;
}

function formatResponse(value) {
  const parts = value.split(/(```[\w]*\n[\s\S]*?```)/g);
  return parts.map((part) => {
    if (part.startsWith("```")) {
      const lines = part.split("\n");
      lines.shift();
      if (lines.at(-1) === "```") lines.pop();
      const code = escapeHtml(lines.join("\n"));
      return `<pre><button class="copy-button" type="button">Copy</button><code>${code}</code></pre>`;
    }
    return escapeHtml(part).replace(/\n/g, "<br>");
  }).join("");
}

function addMessage(role, content, loading = false) {
  const welcome = conversation.querySelector(".welcome");
  if (welcome) welcome.remove();

  const message = document.createElement("article");
  message.className = `message ${role}`;
  if (loading) {
    message.innerHTML = `
      <div class="message-avatar" aria-hidden="true">&lt;/&gt;</div>
      <div class="message-content">
        <div class="message-label">Assistant</div>
        <div class="loading"><span></span><span></span><span></span></div>
      </div>`;
  } else {
    const label = role === "user" ? "You" : "Assistant";
    const avatar = role === "user" ? "YOU" : "&lt;/&gt;";
    const body = role === "assistant" ? formatResponse(content) : `<p class="message-text">${escapeHtml(content)}</p>`;
    message.innerHTML = `
      <div class="message-avatar" aria-hidden="true">${avatar}</div>
      <div class="message-content">
        <div class="message-label">${label}</div>
        ${body}
      </div>`;
  }
  conversation.appendChild(message);
  conversation.scrollTop = conversation.scrollHeight;
  return message;
}

async function sendPrompt(prompt) {
  prompt = prompt.trim();
  if (!prompt) return;

  addMessage("user", prompt);
  promptInput.value = "";
  promptInput.style.height = "auto";
  sendButton.disabled = true;
  promptInput.disabled = true;
  const loadingMessage = addMessage("assistant", "", true);

  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Code generation failed.");
    loadingMessage.remove();
    addMessage("assistant", data.code);
  } catch (error) {
    loadingMessage.remove();
    addMessage("assistant", `Unable to generate code: ${error.message}`);
  } finally {
    sendButton.disabled = false;
    promptInput.disabled = false;
    promptInput.focus();
  }
}

composer.addEventListener("submit", (event) => {
  event.preventDefault();
  sendPrompt(promptInput.value);
});

promptInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendPrompt(promptInput.value);
  }
});

promptInput.addEventListener("input", () => {
  promptInput.style.height = "auto";
  promptInput.style.height = `${Math.min(promptInput.scrollHeight, 180)}px`;
});

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => sendPrompt(button.dataset.prompt));
});

newChat.addEventListener("click", () => {
  conversation.innerHTML = `
    <div class="welcome">
      <div class="welcome-icon" aria-hidden="true">&lt;/&gt;</div>
      <h2>What are we building?</h2>
      <p>Describe a function, API, algorithm, or application in plain language.</p>
      <div class="suggestions">
        <button type="button" data-prompt="Create a Python contact manager using a dictionary"><span>Dictionary app</span><small>Build a small data manager</small></button>
        <button type="button" data-prompt="Write a FastAPI endpoint that returns paginated JSON results"><span>REST endpoint</span><small>Create a FastAPI route</small></button>
        <button type="button" data-prompt="Explain recursion and show a Python example"><span>Learn a concept</span><small>Get an explanation and example</small></button>
      </div>
    </div>`;
  conversation.querySelectorAll("[data-prompt]").forEach((button) => {
    button.addEventListener("click", () => sendPrompt(button.dataset.prompt));
  });
  promptInput.focus();
});

themeToggle.addEventListener("click", () => {
  document.body.classList.toggle("light");
  localStorage.setItem("theme", document.body.classList.contains("light") ? "light" : "dark");
});

if (localStorage.getItem("theme") === "light") document.body.classList.add("light");

conversation.addEventListener("click", async (event) => {
  const button = event.target.closest(".copy-button");
  if (!button) return;
  const code = button.nextElementSibling.textContent;
  await navigator.clipboard.writeText(code);
  button.textContent = "Copied";
  setTimeout(() => { button.textContent = "Copy"; }, 1200);
});

const modelModal = document.getElementById("model-modal");
const modelSettingsButton = document.getElementById("model-settings-button");
const modelModalClose = document.getElementById("model-modal-close");
const modelSettingsForm = document.getElementById("model-settings-form");
const modelSettingsError = document.getElementById("model-settings-error");
const toggleApiKey = document.getElementById("toggle-api-key");
const modelApiKey = document.getElementById("model-api-key");
const providerPreset = document.getElementById("provider-preset");
const providerName = document.getElementById("provider-name");
const baseUrl = document.getElementById("base-url");
const modelName = document.getElementById("model-name");

const providerPresets = {
  nvidia: { name: "NVIDIA", baseUrl: "https://integrate.api.nvidia.com/v1" },
  openai: { name: "OpenAI", baseUrl: "https://api.openai.com/v1", model: "gpt-4o-mini" },
  openrouter: { name: "OpenRouter", baseUrl: "https://openrouter.ai/api/v1" },
};

providerPreset.addEventListener("change", () => {
  const preset = providerPresets[providerPreset.value];
  if (preset) {
    providerName.value = preset.name;
    baseUrl.value = preset.baseUrl;
    modelName.value = preset.model || "";
  } else {
    providerName.value = "Custom";
    baseUrl.value = "";
    modelName.value = "";
  }
});

async function openModelSettings() {
  modelModal.hidden = false;
  try {
    const response = await fetch("/api/models/settings");
    const settings = await response.json();
    providerName.value = settings.provider_name || "Custom";
    const preset = Object.keys(providerPresets).find(
      (key) => providerPresets[key].name.toLowerCase() === providerName.value.toLowerCase(),
    );
    providerPreset.value = preset || "custom";
    baseUrl.value = settings.base_url || "";
    modelName.value = settings.model || "";
    modelApiKey.value = settings.api_key ? "••••••••" : "";
  } catch (_) {}
  modelModalClose.focus();
}

function closeModelSettings() {
  modelModal.hidden = true;
  modelSettingsButton.focus();
}

modelSettingsButton.addEventListener("click", openModelSettings);
modelModalClose.addEventListener("click", closeModelSettings);
modelModal.addEventListener("click", (event) => {
  if (event.target === modelModal) closeModelSettings();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !modelModal.hidden) closeModelSettings();
});

toggleApiKey.addEventListener("click", () => {
  const showing = modelApiKey.type === "text";
  modelApiKey.type = showing ? "password" : "text";
  toggleApiKey.textContent = showing ? "Show" : "Hide";
});

modelSettingsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  modelSettingsError.hidden = true;
  const payload = {
    provider_name: providerName.value,
    api_key: modelApiKey.value,
    base_url: baseUrl.value,
    model: document.getElementById("model-name").value,
  };
  try {
    const response = await fetch("/api/models/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not save model settings.");
    modelSettingsButton.querySelector("span:nth-child(2)").textContent =
      `${data.provider_name} · ${data.model}`;
    closeModelSettings();
  } catch (error) {
    modelSettingsError.textContent = error.message;
    modelSettingsError.hidden = false;
  }
});
