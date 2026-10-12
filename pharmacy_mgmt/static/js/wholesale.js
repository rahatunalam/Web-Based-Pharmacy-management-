const form          = document.getElementById('medicineForm');
const tableBody     = document.getElementById('medicineTableBody');
const hiddenInputs  = document.getElementById('hiddenInputs');
const discountInput = document.getElementById('discount');
const emptyRow      = document.getElementById('emptyRow');

let rowCount        = 0;
let runningSubtotal = 0;
let runningDiscount = 0;   // tracks total discount in taka across all rows

const currency = n => '৳' + parseFloat(n).toLocaleString(
    undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }
);

function updateSummary() {
    // ✅ use runningDiscount — not 'discount' which was never defined
    const finalPrice = Math.max(0, runningSubtotal - runningDiscount);
    const effectivePercent = runningSubtotal > 0
        ? ((runningDiscount / runningSubtotal) * 100).toFixed(1)
        : 0;

    document.getElementById('displaySubtotal').textContent = currency(runningSubtotal);
    // ✅ fixed template literal — use ${} not \( \)
    document.getElementById('displayDiscount').textContent =
        `${currency(runningDiscount)} (${effectivePercent}%)`;
    document.getElementById('displayFinal').textContent    = currency(finalPrice);

    setHidden('subtotal',    runningSubtotal.toFixed(2));
    // ✅ use runningDiscount
    setHidden('discount',    runningDiscount.toFixed(2));
    setHidden('final_price', finalPrice.toFixed(2));
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
    const count = tableBody.querySelectorAll('tr[data-index]').length;
    setHidden('total_count', count);
}

// ✅ fixed — now accepts 4 params correctly (removed unused itemFinalTotal param)
function attachDeleteHandler(button, index, itemTotal, itemDiscount) {
    button.addEventListener('click', () => {
        button.closest('tr').remove();
        hiddenInputs.querySelectorAll(`[data-row="${index}"]`)
            .forEach(input => input.remove());

        runningSubtotal -= itemTotal;
        runningDiscount -= itemDiscount;
        updateTotalCount();
        updateSummary();

        if (tableBody.querySelectorAll('tr[data-index]').length === 0) {
            emptyRow.style.display = '';
        }
    });
}

// Initialize medicine autocomplete
if (typeof initMedicineSearch === 'function') {
    initMedicineSearch((medicine) => {
        const customPriceInput = document.getElementById('customPrice');
        if (customPriceInput) {
            customPriceInput.placeholder = `Default: ৳${medicine.price.toFixed(2)}`;
        }

        // Fill discount field with company's discount percentage
        // User can still edit it manually after this
        if (medicine.discount_pct && medicine.discount_pct> 0){
            discountInput.value = medicine.discount_pct;
        }
        else{
            discountInput.value = 0 ;
        }
        
        document.getElementById('saleQuantity').focus();
    });
}

form.addEventListener('submit', async e => {
    e.preventDefault();

    const name           = document.getElementById('productName').value.trim();
    const quantity       = parseInt(document.getElementById('saleQuantity').value);
    const customPrice    = parseFloat(document.getElementById('customPrice').value);
    const discountPercent = parseFloat(discountInput.value) || 0;

    if (!name || !quantity) return;

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

    const price              = (!isNaN(customPrice) && customPrice > 0) ? customPrice : data.price;
    const itemTotal          = price * quantity;
    const itemDiscountAmount = itemTotal * (discountPercent / 100);
    const itemFinalTotal     = Math.max(0, itemTotal - itemDiscountAmount);
    const index              = rowCount;

    emptyRow.style.display = 'none';

    const row = document.createElement('tr');
    row.dataset.index = index;
    row.innerHTML = `
        <td style="font-weight:600;">${name}</td>
        <td><span class="pill">${data.product_type}</span></td>
        <td class="num">${quantity}</td>
        <td class="num">${currency(price)}</td>
        <td class="num" style="color:var(--data-coral);">${currency(itemDiscountAmount)}</td>
        <td class="num">${currency(itemTotal)}</td>
        <td class="num" style="font-weight:700; color:var(--accent);">${currency(itemFinalTotal)}</td>
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

    // ✅ fixed — pass only 4 args matching the function definition
    attachDeleteHandler(row.querySelector('.row-delete'), index, itemTotal, itemDiscountAmount);

    // Inject hidden inputs — total stores the after-discount amount
    const fields = {
        name,
        type:     data.product_type,
        quantity,
        price,
        total:    itemFinalTotal,
    };
    for (const [key, val] of Object.entries(fields)) {
        const input         = document.createElement('input');
        input.type          = 'hidden';
        input.name          = `sale_${index}_${key}`;
        input.value         = val;
        input.dataset.row   = index;
        hiddenInputs.appendChild(input);
    }

    runningSubtotal += itemTotal;
    runningDiscount += itemDiscountAmount;
    rowCount++;
    updateTotalCount();
    updateSummary();
    form.reset();
    document.getElementById('productName').focus();
});

function submitSale(shouldPrint) {
    const realRows = tableBody.querySelectorAll('tr[data-index]').length;
    if (realRows === 0) {
        alert('Please add at least one medicine before confirming.');
        return;
    }
    // ✅ sync buyer name HERE — not in the submit event listener
    const buyerName = document.getElementById('buyerName').value.trim();
    if (!buyerName) {
        alert('Please enter a buyer name before confirming.');
        document.getElementById('buyerName').focus();
        return;
    }
    setHidden('buyer_name', buyerName);
    setHidden('print', shouldPrint ? '1' : '0');
    document.getElementById('dbForm').submit();
}