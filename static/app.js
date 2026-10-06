document.addEventListener("DOMContentLoaded", () => {
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("fileInput");
    const fileList = document.getElementById("fileList");
    const convertBtn = document.getElementById("convertBtn");
    const deleteCheckbox = document.getElementById("deleteSource");
    const uploadProgress = document.getElementById("uploadProgress");
    const uploadBar = document.getElementById("uploadBar");
    const uploadPercent = document.getElementById("uploadPercent");
    const convProgress = document.getElementById("convProgress");
    const convBar = document.getElementById("convBar");
    const convPercent = document.getElementById("convPercent");
    const convEta = document.getElementById("convEta");
    const statusMsg = document.getElementById("statusMsg");

    let selectedFile = null;
    let eventSource = null;

    function loadFiles() {
        fetch("/api/files")
            .then((r) => r.json())
            .then((files) => {
                fileList.innerHTML = "";
                if (files.length === 0) {
                    fileList.innerHTML = '<li class="empty-state">No hay archivos disponibles</li>';
                    selectedFile = null;
                    updateConvertBtn();
                    return;
                }
                files.forEach((f) => {
                    const li = document.createElement("li");
                    li.innerHTML = `<span class="radio-dot"></span><span class="file-name">${escapeHtml(f.name)}</span><span class="file-size">${f.size_human}</span>`;
                    li.addEventListener("click", () => selectFile(f.name, li));
                    fileList.appendChild(li);
                });
                if (selectedFile) {
                    const items = fileList.querySelectorAll("li");
                    items.forEach((li) => {
                        if (li.querySelector(".file-name")?.textContent === selectedFile) {
                            li.classList.add("selected");
                        }
                    });
                }
                updateConvertBtn();
            });
    }

    function selectFile(name, li) {
        fileList.querySelectorAll("li").forEach((el) => el.classList.remove("selected"));
        li.classList.add("selected");
        selectedFile = name;
        updateConvertBtn();
    }

    function updateConvertBtn() {
        convertBtn.disabled = !selectedFile;
    }

    function showStatus(message, type) {
        statusMsg.textContent = message;
        statusMsg.className = "status-message visible " + type;
    }

    function hideStatus() {
        statusMsg.className = "status-message";
    }

    function formatEta(seconds) {
        if (seconds == null) return "Calculando...";
        if (seconds < 60) return `${seconds}s`;
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        if (m < 60) return `${m}m ${s}s`;
        const h = Math.floor(m / 60);
        return `${h}h ${m % 60}m`;
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    // Drag and drop
    ["dragenter", "dragover"].forEach((evt) => {
        dropzone.addEventListener(evt, (e) => {
            e.preventDefault();
            dropzone.classList.add("dragover");
        });
    });

    ["dragleave", "drop"].forEach((evt) => {
        dropzone.addEventListener(evt, () => {
            dropzone.classList.remove("dragover");
        });
    });

    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        const files = e.dataTransfer.files;
        if (files.length > 0) uploadFile(files[0]);
    });

    dropzone.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) uploadFile(fileInput.files[0]);
    });

    function uploadFile(file) {
        hideStatus();
        const formData = new FormData();
        formData.append("file", file);

        const xhr = new XMLHttpRequest();
        uploadProgress.classList.add("visible");
        uploadBar.style.width = "0%";
        uploadBar.className = "progress-bar-fill";

        xhr.upload.addEventListener("progress", (e) => {
            if (e.lengthComputable) {
                const pct = Math.round((e.loaded / e.total) * 100);
                uploadBar.style.width = pct + "%";
                uploadPercent.textContent = pct + "%";
            }
        });

        xhr.addEventListener("load", () => {
            if (xhr.status === 200) {
                uploadBar.style.width = "100%";
                uploadBar.classList.add("success");
                uploadPercent.textContent = "100%";
                const resp = JSON.parse(xhr.responseText);
                showStatus(resp.message, "success");
                setTimeout(() => {
                    uploadProgress.classList.remove("visible");
                    loadFiles();
                }, 1500);
            } else {
                uploadBar.classList.add("error");
                let msg = "Error al subir el archivo";
                try { msg = JSON.parse(xhr.responseText).error; } catch {}
                showStatus(msg, "error");
            }
            fileInput.value = "";
        });

        xhr.addEventListener("error", () => {
            uploadBar.classList.add("error");
            showStatus("Error de conexión al subir el archivo", "error");
            fileInput.value = "";
        });

        xhr.open("POST", "/api/upload");
        xhr.send(formData);
    }

    // Convert
    convertBtn.addEventListener("click", () => {
        if (!selectedFile) return;
        hideStatus();

        convertBtn.disabled = true;
        convertBtn.textContent = "CONVIRTIENDO...";

        fetch("/api/convert", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                filename: selectedFile,
                delete_source: deleteCheckbox.checked,
            }),
        })
            .then((r) => r.json().then((data) => ({ ok: r.ok, data })))
            .then(({ ok, data }) => {
                if (!ok) {
                    showStatus(data.error, "error");
                    resetConvertBtn();
                    return;
                }
                startProgressStream(selectedFile);
            })
            .catch(() => {
                showStatus("Error de conexión al iniciar la conversión", "error");
                resetConvertBtn();
            });
    });

    function startProgressStream(filename) {
        convProgress.classList.add("visible");
        convBar.style.width = "0%";
        convBar.className = "progress-bar-fill";
        convPercent.textContent = "0%";
        convEta.textContent = "Calculando...";

        if (eventSource) eventSource.close();
        eventSource = new EventSource("/api/progress?filename=" + encodeURIComponent(filename));

        eventSource.onmessage = (e) => {
            const data = JSON.parse(e.data);

            if (data.status === "processing") {
                convBar.style.width = data.percent + "%";
                convPercent.textContent = data.percent + "%";
                convEta.textContent = formatEta(data.eta);
            } else if (data.status === "complete") {
                convBar.style.width = "100%";
                convBar.classList.add("success");
                convPercent.textContent = "100%";
                convEta.textContent = "Completado";
                showStatus("Conversión exitosa: " + filename, "success");
                finish();
            } else if (data.status === "error") {
                convBar.classList.add("error");
                convEta.textContent = "Error";
                showStatus("Error: " + (data.error || "Error desconocido"), "error");
                finish();
            }
        };

        eventSource.onerror = () => {
            showStatus("Se perdió la conexión con el servidor", "error");
            finish();
        };

        function finish() {
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
            resetConvertBtn();
            setTimeout(() => {
                loadFiles();
            }, 2000);
        }
    }

    function resetConvertBtn() {
        convertBtn.textContent = "CONVERTIR";
        convertBtn.disabled = !selectedFile;
    }

    // Test notification buttons
    document.getElementById("testSuccessBtn").addEventListener("click", () => testNotification("success"));
    document.getElementById("testFailBtn").addEventListener("click", () => testNotification("failure"));

    function testNotification(type) {
        const btn = type === "success"
            ? document.getElementById("testSuccessBtn")
            : document.getElementById("testFailBtn");
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = "Enviando...";

        fetch("/api/test-notification", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ type }),
        })
            .then((r) => r.json().then((data) => ({ ok: r.ok, data })))
            .then(({ ok, data }) => {
                if (ok) {
                    showStatus(data.message, "success");
                } else {
                    showStatus(data.error || "Error al enviar notificación", "error");
                }
            })
            .catch(() => {
                showStatus("Error de conexión al enviar notificación", "error");
            })
            .finally(() => {
                btn.disabled = false;
                btn.textContent = originalText;
            });
    }

    loadFiles();
});
