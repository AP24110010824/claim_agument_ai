document.addEventListener("DOMContentLoaded", () => {
    const dropzone = document.getElementById("dropzone");
    const photoInput = document.getElementById("photoInput");
    const dropzonePrompt = document.getElementById("dropzonePrompt");
    const previewContainer = document.getElementById("previewContainer");
    const imagePreview = document.getElementById("imagePreview");
    const btnRemovePhoto = document.getElementById("btnRemovePhoto");

    const claimForm = document.getElementById("claimForm");
    const notesInput = document.getElementById("notesInput");
    const btnSubmit = document.getElementById("btnSubmit");
    const btnText = document.getElementById("btnText");
    const btnSpinner = document.getElementById("btnSpinner");

    const emptyState = document.getElementById("emptyState");
    const resultsContent = document.getElementById("resultsContent");
    const resConfidence = document.getElementById("resConfidence");
    const resDamageType = document.getElementById("resDamageType");
    const resSeverity = document.getElementById("resSeverity");
    const resAction = document.getElementById("resAction");
    const resSummary = document.getElementById("resSummary");
    const galleryGrid = document.getElementById("galleryGrid");

    // 1. Dropzone click & drag-and-drop triggers
    dropzone.addEventListener("click", () => photoInput.click());
    
    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.style.borderColor = "var(--accent)";
    });
    
    dropzone.addEventListener("dragleave", () => {
        dropzone.style.borderColor = "var(--border-color)";
    });

    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.style.borderColor = "var(--border-color)";
        if (e.dataTransfer.files.length > 0) {
            photoInput.files = e.dataTransfer.files;
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    photoInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    function handleFileSelect(file) {
        if (!file.type.startsWith("image/")) {
            alert("Please select a valid image file (JPEG, PNG, WEBP).");
            return;
        }
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            dropzonePrompt.style.display = "none";
            previewContainer.style.display = "block";
        };
        reader.readAsDataURL(file);
    }

    btnRemovePhoto.addEventListener("click", (e) => {
        e.stopPropagation();
        photoInput.value = "";
        imagePreview.src = "";
        previewContainer.style.display = "none";
        dropzonePrompt.style.display = "block";
    });

    // 2. Preset Pills Click Handling
    document.querySelectorAll(".preset-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            notesInput.value = btn.getAttribute("data-preset");
        });
    });

    // 3. Form Submit -> Call /api/process-claim Asynchronously
    claimForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        if (!photoInput.files || photoInput.files.length === 0) {
            alert("Please select or drop a vehicle damage photo first.");
            return;
        }

        const formData = new FormData();
        formData.append("photo", photoInput.files[0]);
        formData.append("notes", notesInput.value.trim());

        // Set Loading State
        btnSubmit.disabled = true;
        btnText.textContent = "Processing Claim (OpenCV + Groq AI)...";
        btnSpinner.style.display = "inline-block";

        try {
            const response = await fetch("/api/process-claim", {
                method: "POST",
                body: formData
            });

            const result = await response.json();

            if (!response.ok || result.status !== "success") {
                throw new Error(result.message || "Failed to process claim.");
            }

            renderResults(result.data);

        } catch (error) {
            alert(`Error: ${error.message}`);
        } finally {
            // Restore Button State
            btnSubmit.disabled = false;
            btnText.textContent = "⚡ Process Claim & Generate Dataset";
            btnSpinner.style.display = "none";
        }
    });

    // 4. Render Results Function
    function renderResults(data) {
        emptyState.style.display = "none";
        resultsContent.style.display = "block";

        const ai = data.ai_assessment;
        resConfidence.textContent = `Confidence: ${(ai.confidence_score * 100).toFixed(0)}%`;
        resDamageType.textContent = ai.damage_type;
        
        resSeverity.textContent = ai.severity;
        resSeverity.className = "metric-value severity-badge " + ai.severity.toLowerCase();

        resAction.textContent = ai.estimated_action;
        resSummary.textContent = `"${ai.summary}"`;

        // Render Dataset Gallery
        galleryGrid.innerHTML = "";

        // Add Original First
        const originalCard = createCard(data.original_image.url, "Original Photo", "Source");
        galleryGrid.appendChild(originalCard);

        // Add 5 Augmented
        data.augmented_images.forEach((item) => {
            const card = createCard(item.url, item.effect, "Augmented");
            galleryGrid.appendChild(card);
        });
    }

    function createCard(url, title, type) {
        const div = document.createElement("div");
        div.className = "gallery-item";
        div.innerHTML = `
            <img src="${url}" alt="${title}" loading="lazy">
            <div class="gallery-meta">
                <span class="effect-tag">${title.replace('_', ' ')}</span>
                <a href="${url}" download class="download-link" title="Download Image">⬇️ Save</a>
            </div>
        `;
        return div;
    }
});