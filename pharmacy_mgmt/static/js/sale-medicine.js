const form          = document.getElementById('medicineForm');
const tableBody     = document.getElementById('medicineTableBody');
const hiddenInputs  = document.getElementById('hiddenInputs');
const discountInput = document.getElementById('discount');
const emptyRow      = document.getElementById('emptyRow');
// Initialize medicine search — fills price from dropdown selection
initMedicineSearch((medicine) => {
    // When user selects from dropdown, focus quantity field
    document.getElementById('saleQuantity').focus();
});

let rowCount        = 0;
let runningSubtotal = 0;

const currency = n => '৳' + parseFloat(n).toLocaleString(
    undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }
);

function updateSummary() {
    // Read as percentage, calculate taka amount
    const discountPercent = parseFloat(discountInput.value) || 0;
    const discount        = runningSubtotal * (discountPercent / 100);
    const finalPrice      = Math.max(0, runningSubtotal - discount);

    document.getElementById('displaySubtotal').textContent = currency(runningSubtotal);
    document.getElementById('displayDiscount').textContent = currency(discount) + ` (${discountPercent}%)`;
    document.getElementById('displayFinal').textContent    = currency(finalPrice);

    // Save taka amount to hidden inputs — view stores taka, not percent
    setHidden('subtotal',    runningSubtotal);
    setHidden('discount',    discount);
    setHidden('final_price', finalPrice);
}

function setHidden(name, value) {
    let input = document.getElementById('hidden_' + name);
    if (!input) {
        input        = document.createElement('input');
        input.type   = 'hidden';
        input.id     = 'hidden_' + name;
        input.name   = name;
        hiddenInputs.appendChild(input);
    }
    input.value = value;
}

function updateTotalCount() {
    // ✅ Only count rows with data-index — ignores the emptyRow placeholder
    const count = tableBody.querySelectorAll('tr[data-index]').length;
    setHidden('total_count', count);

    // Update the badge in the card header
    const badge = document.getElementById('itemCount');
    if (badge) badge.textContent = count + (count === 1 ? ' item' : ' items');
}

function attachDeleteHandler(button, index, itemTotal) {
    button.addEventListener('click', () => {
        button.closest('tr').remove();
        hiddenInputs.querySelectorAll(`[data-row="${index}"]`)
            .forEach(input => input.remove());

        runningSubtotal -= itemTotal;
        updateTotalCount();
        updateSummary();

        // Show empty message again if no rows left
        if (emptyRow && tableBody.querySelectorAll('tr[data-index]').length === 0) {
            emptyRow.style.display = '';
        }
    });
}

function submitSale(shouldPrint) {
    const realRows = tableBody.querySelectorAll('tr[data-index]').length;
    if (realRows === 0) {
        alert('Please add at least one medicine before confirming.');
        return;
    }
    setHidden('print', shouldPrint ? '1' : '0');
    document.getElementById('dbForm').submit();
}

discountInput.addEventListener('input', updateSummary);

form.addEventListener('submit', async e => {
    e.preventDefault();

    const name     = document.getElementById('productName').value.trim();
    const quantity = parseInt(document.getElementById('saleQuantity').value);

    if (!name || !quantity) return;

    const response = await fetch(
        `/get-medicine-price/?name=${encodeURIComponent(name)}`
    );
    const data = await response.json();

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

    // Hide the empty placeholder
    if (emptyRow) emptyRow.style.display = 'none';

    // Add row with data-index so updateTotalCount can find it
    const row = document.createElement('tr');
    row.dataset.index = index;   // ✅ required for tr[data-index] selector
    row.innerHTML = `
        <td style="color:var(--ink-faint); font-size:12px;">
            ${rowCount + 1}
        </td>
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

    // Inject hidden inputs for this row
    const fields = { name, quantity, price, total: itemTotal };
    for (const [key, val] of Object.entries(fields)) {
        const input       = document.createElement('input');
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