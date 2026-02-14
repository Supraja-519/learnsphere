document.addEventListener('DOMContentLoaded', () => {
    // --- Gamification State ---
    // State is now largely managed by the server and injected via template, 
    // but we might want to track current session changes dynamically.

    const xpDisplay = document.getElementById('xp-display');
    const streakDisplay = document.getElementById('streak-display');
    const toast = document.getElementById('toast');

    function showToast(message) {
        toast.innerText = message;
        toast.classList.remove('hidden');
        toast.classList.add('visible');
        setTimeout(() => {
            toast.classList.remove('visible');
            setTimeout(() => toast.classList.add('hidden'), 300);
        }, 3000);
    }

    // --- Modal Logic ---
    const modal = document.getElementById('learning-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body-content');
    const loader = document.querySelector('.loader-container');
    const contentDisplay = document.querySelector('.content-display');
    const closeBtn = document.querySelector('.close-modal');
    const tabs = document.querySelectorAll('.tab-btn');
    const completeBtn = document.getElementById('mark-complete-btn');

    let currentNodeId = null;
    let currentNodeTitle = null;
    let currentMode = 'eli5';
    let currentCard = null; // Reference to the clicked card
    const contentCache = {};

    // Open Modal
    document.querySelectorAll('.node-card').forEach(card => {
        card.addEventListener('click', () => {
            // Optional: Check if locked (if we implement strict locking)
            // if (card.querySelector('.fa-lock')) { ... }

            currentNodeId = card.dataset.nodeId;
            currentNodeTitle = card.dataset.nodeTitle;
            currentCard = card;

            modalTitle.innerText = currentNodeTitle;
            modal.classList.remove('hidden');
            setTimeout(() => modal.classList.add('visible'), 10);

            // Reset to default tab
            switchTab('eli5');
        });
    });

    // Close Modal
    closeBtn.addEventListener('click', () => {
        modal.classList.remove('visible');
        setTimeout(() => modal.classList.add('hidden'), 300);
    });

    // Tab Switching
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            switchTab(tab.dataset.mode);
        });
    });

    // Load Content
    async function switchTab(mode) {
        currentMode = mode;
        const cacheKey = `${currentNodeId}_${mode}`;

        contentDisplay.innerHTML = '';
        loader.classList.remove('hidden');
        contentDisplay.classList.add('hidden');

        if (contentCache[cacheKey]) {
            renderContent(contentCache[cacheKey]);
        } else {
            try {
                const response = await fetch('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ node_title: currentNodeTitle, mode: mode })
                });
                const data = await response.json();

                if (data.error) throw new Error(data.error);

                contentCache[cacheKey] = data.content;
                renderContent(data.content);

            } catch (err) {
                renderContent(`**Error:** ${err.message}. Please try again.`);
            }
        }
    }

    function renderContent(markdownText) {
        loader.classList.add('hidden');
        contentDisplay.classList.remove('hidden');
        contentDisplay.innerHTML = marked.parse(markdownText);
        contentDisplay.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });
    }

    // Complete Button (Sync with Backend)
    completeBtn.addEventListener('click', async () => {
        try {
            const response = await fetch('/api/complete_node', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ node_id: currentNodeId })
            });
            const data = await response.json();

            if (data.success) {
                showToast(data.message);

                // Update UI State
                if (currentCard) {
                    currentCard.classList.add('completed');
                    const icon = currentCard.querySelector('.node-status i');
                    icon.className = 'fa-solid fa-check';
                }

                // Update XP
                xpDisplay.innerText = `${data.xp} XP`;

            } else {
                showToast("Something went wrong.");
            }
        } catch (e) {
            console.error(e);
            showToast("Connection error.");
        }
    });

    // Add dynamic styles if needed again, mainly done in CSS now.
});
