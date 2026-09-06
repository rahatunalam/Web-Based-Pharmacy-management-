// ── Customer search ─────────────────────────────────────
const customerSearch   = document.getElementById('customerSearch');
const customerDropdown = document.getElementById('customerDropdown');
const selectedBadge    = document.getElementById('selectedCustomerBadge');
const selectedText     = document.getElementById('selectedCustomerText');
const clearBtn         = document.getElementById('clearCustomer');

initMedicineSearch((medicine) => {
    document.getElementById('saleQuantity').focus();
});

let selectedCustomerId = null;
let customerDebounce   = null;

customerSearch.addEventListener('input', () => {
    const query = customerSearch.value.trim();
    clearTimeout(customerDebounce);

    if (query.length < 1) {
        closeCustomerDropdown();
        return;
    }

    customerDebounce = setTimeout(async () => {
        const res  = await fetch(
            `/get-pro-customers/?q=${encodeURIComponent(query)}`
        );
        const data = await res.json();

        customerDropdown.innerHTML = '';

        if (data.customers.length === 0) {
            customerDropdown.innerHTML =
                '<div class="customer-option" style="color:var(--ink-faint);">' +
                'No customers found.</div>';
            customerDropdown.classList.add('is-open');
            return;
        }

        data.customers.forEach(c => {
            const item = document.createElement('div');
            item.className = 'customer-option';
            item.innerHTML = `${c.name}<span class="phone">${c.phone_number}</span>`;

            item.addEventListener('click', () => {
                // Store customer ID and show selected badge
                selectedCustomerId = c.id;
                selectedText.textContent =
                    `${c.name}  •  ${c.phone_number}`;
                selectedBadge.classList.add('is-visible');
                customerSearch.style.display = 'none';
                closeCustomerDropdown();

                // Inject customer_id hidden input into dbForm
                setHidden('customer_id', c.id);
            });

            customerDropdown.appendChild(item);
        });

        customerDropdown.classList.add('is-open');
    }, 250);
});

clearBtn.addEventListener('click', () => {
    selectedCustomerId = null;
    selectedBadge.classList.remove('is-visible');
    customerSearch.style.display = '';
    customerSearch.value = '';
    customerSearch.focus();

    // Remove the customer_id hidden input
    const existing = document.getElementById('hidden_customer_id');
    if (existing) existing.remove();
});

function closeCustomerDropdown() {
    customerDropdown.classList.remove('is-open');
}

document.addEventListener('click', e => {
    if (!customerSearch.contains(e.target) &&
        !customerDropdown.contains(e.target)) {
        closeCustomerDropdown();
    }
});

// ── Medicine table + summary ────────────────────────────
const form          = document.getElementById('medicineForm');
const tableBody     = document.getElementById('medicineTableBody');
const hiddenInputs  = document.getElementById('hiddenInputs');
const discountInput = document.getElementById('discount');
const emptyRow      = document.getElementById('emptyRow');

let rowCount        = 0;
let runningSubtotal = 0;

const currency = n => '৳' + parseFloat(n).toLocaleString(
    undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }
);

function setHidden(name, value) {
    let input = document.getElementById('hidden_' + name);
    if (!input) {
        input = document.createElement('input');
        input.type = 'hidden';
        input.id   = 'hidden_' + name;
        input.name = name;
        hiddenInputs.appendChild(input);
    }
    input.value = value;
}

function updateSummary() {
    const discountPercent   = parseFloat(discountInput.value) || 0;
    const discount   = runningSubtotal*(discountPercent/100);
    const finalPrice = Math.max(0, runningSubtotal - discount);

    document.getElementById('displaySubtotal').textContent = currency(runningSubtotal);
    document.getElementById('displayDiscount').textContent = currency(discount);
    document.getElementById('displayFinal').textContent    = currency(finalPrice);

    setHidden('subtotal',    runningSubtotal);
    setHidden('discount',    discount);
    setHidden('final_price', finalPrice);
}

function updateTotalCount() {
    setHidden('total_count',
        tableBody.querySelectorAll('tr[data-index]').length
    );
}

function attachDeleteHandler(button, index, itemTotal) {
    button.addEventListener('click', () => {
        button.closest('tr').remove();
        hiddenInputs.querySelectorAll(`[data-row="${index}"]`)
            .forEach(input => input.remove());

        runningSubtotal -= itemTotal;
        updateTotalCount();
        updateSummary();

        if (tableBody.querySelectorAll('tr[data-index]').length === 0) {
            emptyRow.style.display = '';
        }
    });
}

discountInput.addEventListener('input', updateSummary);

// Validate customer is selected before submitting
document.getElementById('dbForm').addEventListener('submit', e => {
    if (!selectedCustomerId) {
        e.preventDefault();
        alert('Please select a pro customer before confirming the sale.');
        customerSearch.focus();
    }
});

form.addEventListener('submit', async e => {
    e.preventDefault();

    if (!selectedCustomerId) {
        alert('Please select a pro customer first.');
        return;
    }

    const name     = document.getElementById('productName').value.trim();
    const quantity = parseInt(document.getElementById('saleQuantity').value);

    if (!name || !quantity) return;

    const res  = await fetch(
        `/get-pro-customer-price/?name=${encodeURIComponent(name)}`
    );
    const data = await res.json();

    if (!data.found) {
        alert(`Medicine "${name}" not found in database.`);
        return;
    }

    if (quantity > data.stock) {
        alert(
            `Not enough stock for "${name}". ` +
            `Available: ${data.stock}, Requested: ${quantity}.`
        );
        return;
    }

    const price     = data.price;
    const itemTotal = price * quantity;
    const index     = rowCount;

    emptyRow.style.display = 'none';

    const row = document.createElement('tr');
    row.dataset.index = index;
    row.innerHTML = `
        <td style="font-weight:600;">${name}</td>
        <td><span class="pill">${data.product_type}</span></td>
        <td class="num">${quantity}</td>
        <td class="num">${currency(price)}</td>
        <td class="num">${currency(itemTotal)}</td>
        <td>
            <button type="button" class="row-delete">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none"
                    stroke="currentColor" stroke-width="2"
                    stroke-linecap="round" stroke-linejoin="round">
                    <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1
                        2 2v2m3 0-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 6"/>
                </svg>
            </button>
        </td>
    `;
    tableBody.appendChild(row);
    attachDeleteHandler(row.querySelector('.row-delete'), index, itemTotal);

    const fields = { name, quantity, price, total: itemTotal };
    for (const [key, val] of Object.entries(fields)) {
        const input = document.createElement('input');
        input.type        = 'hidden';
        input.name        = `sale_${index}_${key}`;
        input.value       = val;
        input.dataset.row = index;
        hiddenInputs.appendChild(input);
    }

    runningSubtotal += itemTotal;
    rowCount++;
    updateTotalCount();
    updateSummary();
    form.reset();
    document.getElementById('productName').focus();
});