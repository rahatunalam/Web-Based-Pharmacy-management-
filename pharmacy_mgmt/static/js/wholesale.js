const form          = document.getElementById('medicineForm');
const tableBody     = document.getElementById('medicineTableBody');
const hiddenInputs  = document.getElementById('hiddenInputs');
const discountInput = document.getElementById('discount');
const emptyRow      = document.getElementById('emptyRow');

initMedicineSearch((medicine) => {
    // Optionally fill the custom price field with the default price
    const customPriceInput = document.getElementById('customPrice');
    if (customPriceInput) {
        customPriceInput.placeholder = `Default: ৳${medicine.price.toFixed(2)}`;
    }
    document.getElementById('saleQuantity').focus();
});

let rowCount = 0;
let runningSubtotal = 0;

const currency = n => '৳' + parseFloat(n).toLocaleString(
    undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }
);

function updateSummary() {
    const discountPercent = parseFloat(discountInput.value) || 0;
    const discount   = runningSubtotal*(discountPercent/100);
    const finalPrice = Math.max(0, runningSubtotal - discount);

    document.getElementById('displaySubtotal').textContent = currency(runningSubtotal);
    document.getElementById('displayDiscount').textContent = currency(discount);
    document.getElementById('displayFinal').textContent    = currency(finalPrice);

    setHidden('subtotal',    runningSubtotal);
    setHidden('discount',    discount);
    setHidden('final_price', finalPrice);
}

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

function updateTotalCount() {
    // Count real rows only — not the empty placeholder row
    const realRows = tableBody.querySelectorAll('tr[data-index]').length;
    setHidden('total_count', realRows);
}

function attachDeleteHandler(button, index, itemTotal) {
    button.addEventListener('click', () => {
        button.closest('tr').remove();
        hiddenInputs.querySelectorAll(`[data-row="${index}"]`)
            .forEach(input => input.remove());

        runningSubtotal -= itemTotal;
        updateTotalCount();
        updateSummary();

        // Show empty message if no rows left
        if (tableBody.querySelectorAll('tr[data-index]').length === 0) {
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

// Sync buyer name into hidden input before submitting
document.getElementById('dbForm').addEventListener('submit', () => {
    setHidden('buyer_name', document.getElementById('buyerName').value.trim());
});

form.addEventListener('submit', async e => {
    e.preventDefault();

    const name        = document.getElementById('productName').value.trim();
    const quantity    = parseInt(document.getElementById('saleQuantity').value);
    const customPrice = parseFloat(document.getElementById('customPrice').value);

    if (!name || !quantity) return;

    // Fetch default price and stock from server
    const response = await fetch(
        `/get-wholesale-price/?name=${encodeURIComponent(name)}`
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

    // Use custom price if provided, otherwise use database price
    const price     = (!isNaN(customPrice) && customPrice > 0)
                        ? customPrice
                        : data.price;
    const itemTotal = price * quantity;
    const index     = rowCount;

    // Hide the empty placeholder row
    emptyRow.style.display = 'none';

    // Add row to table
    const row = document.createElement('tr');
    row.dataset.index = index;   // mark as a real data row
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

    // Inject hidden inputs for Django
    const fields = { name, quantity, price, total: itemTotal };
    for (const [key, val] of Object.entries(fields)) {
        const input = document.createElement('input');
        input.type      = 'hidden';
        input.name      = `sale_${index}_${key}`;
        input.value     = val;
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