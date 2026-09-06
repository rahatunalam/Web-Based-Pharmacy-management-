function initMedicineSearch(onSelect) {
    const input    = document.getElementById('productName');
    const dropdown = document.getElementById('medicineDropdown');

    if (!input || !dropdown) return;

    let debounceTimer  = null;
    let highlighted    = -1;
    let currentResults = [];

    input.addEventListener('input', () => {
        const query = input.value.trim();
        clearTimeout(debounceTimer);

        if (query.length < 1) {
            closeDropdown();
            return;
        }

        debounceTimer = setTimeout(() => fetchMedicines(query), 250);
    });

    async function fetchMedicines(query) {
        const res  = await fetch(
            `/medicine-search/?q=${encodeURIComponent(query)}`
        );
        const data = await res.json();
        currentResults = data.results;
        renderDropdown(data.results);
    }

    function renderDropdown(results) {
        dropdown.innerHTML = '';
        highlighted = -1;

        if (results.length === 0) {
            dropdown.innerHTML = `
                <div class="medicine-option"
                  style="color:var(--ink-faint); cursor:default;">
                  No medicines found
                </div>`;
            dropdown.classList.add('is-open');
            return;
        }

        results.forEach((m, i) => {
            const isLow  = m.quantity < 10;
            const item   = document.createElement('div');
            item.className = 'medicine-option';
            item.dataset.index = i;
            item.innerHTML = `
                <div class="medicine-option__left">
                    <span class="medicine-option__name">${m.name}</span>
                    <span class="medicine-option__type">${m.product_type}</span>
                </div>
                <div class="medicine-option__right">
                    <span class="medicine-option__price">৳${m.price.toFixed(2)}</span>
                    <span class="medicine-option__stock ${isLow ? 'low' : 'ok'}">
                        ${isLow ? '⚠ ' : ''}Stock: ${m.quantity}
                    </span>
                </div>
            `;

            item.addEventListener('click', () => selectMedicine(m));
            dropdown.appendChild(item);
        });

        dropdown.classList.add('is-open');
    }

    function selectMedicine(m) {
        // Fill the input with the selected name
        input.value = m.name;
        closeDropdown();

        // Call the page-specific callback with the medicine data
        if (onSelect) onSelect(m);
    }

    // Keyboard navigation
    input.addEventListener('keydown', e => {
        const items = dropdown.querySelectorAll('.medicine-option[data-index]');

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            highlighted = Math.min(highlighted + 1, items.length - 1);
            updateHighlight(items);

        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            highlighted = Math.max(highlighted - 1, 0);
            updateHighlight(items);

        } else if (e.key === 'Enter' && highlighted >= 0) {
            e.preventDefault();
            const m = currentResults[highlighted];
            if (m) selectMedicine(m);

        } else if (e.key === 'Escape') {
            closeDropdown();
        }
    });

    function updateHighlight(items) {
        items.forEach((item, i) => {
            item.style.background = i === highlighted
                ? 'var(--accent-soft)' : '';
            item.style.color = i === highlighted
                ? 'var(--accent-dark)' : '';
        });
    }

    function closeDropdown() {
        dropdown.classList.remove('is-open');
        dropdown.innerHTML = '';
        highlighted    = -1;
        currentResults = [];
    }

    // Close when clicking outside
    document.addEventListener('click', e => {
        if (!input.contains(e.target) && !dropdown.contains(e.target)) {
            closeDropdown();
        }
    });
}