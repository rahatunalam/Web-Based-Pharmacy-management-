const form         = document.getElementById('medicineForm');
const tableBody    = document.getElementById('medicineTableBody');
const hiddenInputs = document.getElementById('hiddenInputs');
const discountInput = document.getElementById('discount');

let rowCount = 0;
let runningSubtotal = 0;

const currency = n => '৳' + parseFloat(n).toLocaleString(
    undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }
);

// Updates the three summary display values
function updateSummary() {
    const discount   = parseFloat(discountInput.value) || 0;
    const finalPrice = Math.max(0, runningSubtotal - discount);

    document.getElementById('displaySubtotal').textContent = currency(runningSubtotal);
    document.getElementById('displayDiscount').textContent = currency(discount);
    document.getElementById('displayFinal').textContent    = currency(finalPrice);

    // Keep hidden inputs in dbForm up to date
    setHidden('subtotal',    runningSubtotal);
    setHidden('discount',    discount);
    setHidden('final_price', finalPrice);
}

// Creates or updates a single hidden input inside dbForm
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
    setHidden('total_count', tableBody.querySelectorAll('tr').length);
}

function attachDeleteHandler(button, index, itemTotal) {
    button.addEventListener('click', () => {
        button.closest('tr').remove();
        hiddenInputs.querySelectorAll(`[data-row="${index}"]`)
            .forEach(input => input.remove());

        // Subtract this row's total from the running subtotal
        runningSubtotal -= itemTotal;
        updateTotalCount();
        updateSummary();
    });
}

// Recalculate whenever discount field changes
discountInput.addEventListener('input', updateSummary);

// Add button — fetch price from Django then add row
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

    // Add visual row to table
    const row = document.createElement('tr');
    row.innerHTML = `
        <td>${name}</td>
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
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = `sale_${index}_${key}`;
        input.value = val;
        input.dataset.row = index;
        hiddenInputs.appendChild(input);
    }

    // Update running totals
    runningSubtotal += itemTotal;
    rowCount++;
    updateTotalCount();
    updateSummary();
    form.reset();
    document.getElementById('productName').focus();
});