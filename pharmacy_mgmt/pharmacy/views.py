from decimal import Decimal, InvalidOperation
from itertools import groupby
import zoneinfo

from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Max, Sum,Count,F
from django.db.models.functions import TruncMonth,TruncYear
from django.template import context
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import LoginForm
from .models import Medicine,Sale,Wholesale,Purchase,ProCustomer,ProCustomerSale,Company,Invoice
from datetime import timedelta,date
import calendar
import json

# Create your views here.
# Login view
def login_view(request):
    form = LoginForm()

    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request,username=username,password=password)

        if user is not None:
            login(request,user)

            # Admin redirect
            if user.is_superuser:
                return redirect('pharmacy:dashboard')
            else:
                return redirect('pharmacy:sale_medicines')
        
        return render( request,"pharmacy/login.html",{"error": "Invalid username or password"})
        
    return render(request, 'pharmacy/login.html')

@login_required
def dashboard(request):
    # ── KPI Cards ──────────────────────────────────────────

    # Total revenue from all sales (final price after discount)
    total_sales = float(Sale.objects.aggregate(total=Sum('final_price'))['total'] or 0
)
    # Total stock value (quantity × price per unit for every medicine)
    total_stock_value = float(Medicine.objects.aggregate(total=Sum(F('quantity')*F('price_per_unit')))['total'] or 0)

    # Net profit = revenue - stock cost
    net_profit = total_sales - total_stock_value

    # Count medicines with quantity below 10
    low_stock_count = Medicine.objects.filter(quantity__lt = 10).count()

    # ── Donut Chart — stock distribution by medicine ────────
    # Groups sold quantity by medicine name
    distribution_qs = Sale.objects.values('medicine__name').annotate(units=Sum('quantity_sold')).order_by('-units')[:6]

    distribution_chart = {
        'labels': [row['medicine__name'] for row in distribution_qs],
        'values': [row['units'] for row in distribution_qs],
    }

    # ── Bar Chart — monthly sale quantity ───────────────────
    monthly_sales_qs = Sale.objects.annotate(month=TruncMonth('sold_at')).values('month').annotate(units=Sum('quantity_sold')).order_by('month')
    monthly_chart={
        'labels': [row['month'].strftime('%b %Y') for row in monthly_sales_qs],
        'values': [row['units'] for row in monthly_sales_qs],
    }

    # ── Line Chart — yearly revenue trend ──────────────────
    yearly_qs = Sale.objects.annotate(year=TruncYear('sold_at')).values('year').annotate(revenue=Sum('final_price')).order_by('year')
    yearly_chart = {
        'labels': [row['year'].strftime('%Y') for row in yearly_qs],
        'values': [float(row['revenue']) for row in yearly_qs],
    }

    # ── Low stock medicines for the alert card ──────────────
    low_stock_items = Medicine.objects.filter(quantity__lt=10).order_by('quantity')

    # ── Top selling medicines ───────────────────────────────
    top_medicines = Sale.objects.values('medicine__name').annotate(units=Sum('quantity_sold')).order_by('-units')[:5]

    context = {
        'total_sales':       total_sales,
        'total_stock_value': total_stock_value,
        'net_profit':        net_profit,
        'low_stock_count':   low_stock_count,
        'low_stock_items':   low_stock_items,
        'top_medicines':     top_medicines,

        # Serialize to JSON so Chart.js can read them in the template
        'distribution_chart': json.dumps(distribution_chart),
        'monthly_chart':      json.dumps(monthly_chart),
        'yearly_chart':       json.dumps(yearly_chart),
    }
    return render(request,'pharmacy/index.html',context)

# Logout view
def logout_view(request):
    logout(request)
    return redirect('pharmacy:login') # redirct to login function

# Add Medicine
@login_required
def add_medicine(request):

    if request.method == 'POST':
        total_count = int(request.POST.get('total_count',0))

        for i in range(total_count):
            name = request.POST.get(f'medicine_{i}_name')
            company = request.POST.get(f'medicine_{i}_company')
            type_ = request.POST.get(f'medicine_{i}_type')
            quantity = request.POST.get(f'medicine_{i}_quantity')
            price = request.POST.get(f'medicine_{i}_price')
            invoice_number = request.POST.get(f'medicine_{i}_invoice', '')  # ← add
            total_price = request.POST.get(f'medicine_{i}_total_price')
            total_dis_price = request.POST.get(f'medicine_{i}_total_dis_price')

            if name and type_ and quantity and price:
                quantity= int(quantity)
                price =  float(price)
                total_price = float(total_price)
                total_dis_price = float(total_dis_price or total_price)

                # Check for an existing medicine with the same name + type
                existing = Medicine.objects.filter(
                    name__iexact=name,
                    product_type__iexact=type_
                ).order_by('id').first()

                if existing:
                    # Restock: add to existing quantity, update price to the new one
                    existing.quantity += quantity
                    existing.price_per_unit = price
                    existing.total_price = (existing.total_price or 0) + total_price
                    if company:
                        existing.company = company
                    if invoice_number:
                        existing.invoice_number = invoice_number
                    existing.save()
                    medicine = existing

                else:
                    medicine = Medicine.objects.create(
                        name=name,
                        company=company, 
                        product_type=type_,
                        quantity=int(quantity),
                        price_per_unit=float(price),
                        total_price =float(total_price),
                        total_dis_price = float(total_dis_price),
                    )
                # 2. Now create the Purchase record, referencing the real medicine
                Purchase.objects.create(
                    medicine=medicine,
                    company=company or '',
                    quantity=quantity,
                    price_per_unit=price,
                    invoice_number=invoice_number,
                    total_cost=quantity * price,
                    total_dis_price= float(total_dis_price),
                    added_by=request.user,
                )

                if company and invoice_number:
                    company_obj = Company.objects.filter(company__iexact=company).first()
                    if not company_obj:
                        company_obj = Company.objects.create(company=company)

                    invoice_exists = Invoice.objects.filter(
                        company=company_obj,
                        invoice_number__iexact=invoice_number
                    ).exists()
                    if not invoice_exists:
                        Invoice.objects.create(company=company_obj, invoice_number=invoice_number)
        return redirect('pharmacy:add_medicine')
                 
    return render(request,'pharmacy/add-medicine.html')

@login_required
def get_companies(request):
    companies = Company.objects.all().order_by('company')
    return JsonResponse({
        'companies': [{'id': c.pk, 'name': c.company, 'discount': str(c.discount_price)} for c in companies]
    })

@login_required
def add_company_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'success':False,'error': 'Invalid request.'})
    name = request.POST.get('company_name','').strip()
    discount_raw = request.POST.get('discount', '0').strip() or '0'
    if not name:
        return JsonResponse({'success': False, 'error': 'Company name is required.'})

    try:
        discount = Decimal(discount_raw)
    except InvalidOperation:
        return JsonResponse({'success': False, 'error': 'Discount must be a valid number.'})

    if discount < 0 or discount > 100:
        return JsonResponse({'success': False, 'error': 'Discount must be between 0 and 100.'})

    company = Company.objects.filter(company__iexact=name).first()

    if company:
        # Company already exists: update its discount to the newly entered value
        company.discount_price = discount
        company.save()
    else:
        company = Company.objects.create(company=name, discount_price=discount)

    return JsonResponse({'success': True, 'id': company.pk, 'name': company.company,'discount': str(company.discount_price),})


@login_required
def edit_medicine(request):
    
    search = request.GET.get('search', '').strip()
    #invoice = request.GET.get('invoice', '').strip()

    medicines = Medicine.objects.all().order_by('id')

    if search:
        medicines = medicines.filter(name__icontains=search)

    return render(request, 'pharmacy/edit-medicine.html', {
        'medicines': medicines,
        'search': search,
    })

@login_required
def edit_medicine_save(request,pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name','').strip()
        company = request.POST.get('company','').strip()
        quantity = request.POST.get('quantity','').strip()
        price = request.POST.get('price','').strip()

        errors = []

        if not name :
            errors.append('Producct name is required.')
        if not company:
            errors.append('Company name is required')
        if not quantity or not quantity.isdigit():
            errors.append('Quantity must be a valid number.')

        parsed_price = None
        try:
            parsed_price=float(price)
        except(ValueError,TypeError):
            errors.append('Price must be a vlaid number.')

        parsed_qty = None
        try:
            parsed_qty = int(quantity)
        except(ValueError,TypeError):
            errors.append('Quantity must be a vlaid number.')

        if errors:
            # Re-render the list with the inline form open
            search    = request.GET.get('search', '').strip()
            medicines = Medicine.objects.all().order_by('name')
            return render(request, 'pharmacy/edit-medicine.html', {
                'medicines':    medicines,
                'search':       search,
                'editing_pk':   pk,
                'edit_errors':  errors,
                'edit_values': {
                    'name':     name,
                    'company':  company,
                    'quantity': quantity,
                    'price':    price,
                },
            })
        medicine.name = name
        medicine.company = company
        medicine.quantity = parsed_qty
        medicine.price_per_unit = parsed_price
        medicine.total_price = round(parsed_price*parsed_qty,2)
        medicine.save()

        return redirect(
            f"{request.build_absolute_uri('/')[:-1]}"
            f"/edit-medicine/?search={name}"
        )
    
    return redirect('pharmacy:edit_medicine')

@login_required
def delete_med(request,pk):
    if request.method == 'POST':
        medicine = get_object_or_404(Medicine, pk=pk)
        #purchase = get_object_or_404(Purchase, pk=pk)
        medicine.delete()
    return redirect('pharmacy:delete_med')

def _build_invoice_groups(request):
    company_query = request.GET.get('company', '').strip()
    invoice_query = request.GET.get('invoice', '').strip()

    purchases = Purchase.objects.select_related('medicine').all()

    if company_query:
        purchases = purchases.filter(company__icontains=company_query)
    if invoice_query:
        purchases = purchases.filter(invoice_number__icontains=invoice_query)

    purchases = purchases.order_by('company', 'invoice_number')
    invoice_groups = []
    for (company, invoice_number), items in groupby(
        purchases, key=lambda p: (p.company, p.invoice_number)
    ):
        invoice_groups.append({
            'company': company,
            'invoice_number': invoice_number,
            'items': list(items),
        })

    return invoice_groups, purchases.count(), company_query, invoice_query

@login_required
def edit_invoice_medicine(request):
    invoice_groups, total_count, company_query, invoice_query = _build_invoice_groups(request)

    return render(request,'pharmacy/edit-invoice-medicine.html',{
        'invoice_groups': invoice_groups,
        'total_purchases': total_count,
        'company_query': company_query,
        'invoice_query': invoice_query,
    })

@login_required
def edit_invoice_medicine_save(request,pk):
    purchase = get_object_or_404(Purchase,pk=pk)

    if request.method == 'POST':
        quantity = request.POST.get('quantity')
        price = request.POST.get('price')

        edit_errors = []
        if not quantity:
            edit_errors.append('Quantity is required.')
        if not price:
            edit_errors.append('Price is required.')

        if not edit_errors:
            try:
                new_quantity = int(quantity)
                new_price = float(price)
                if new_quantity < 0 or new_price < 0:
                    edit_errors.append('Quantity and price must be zero or positive.')
            except ValueError:
                edit_errors.append('Quantity and price must be valid numbers.')
        if edit_errors:
            invoice_groups, total_count, company_query, invoice_query = _build_invoice_groups(request)
            return render(request, 'pharmacy/edit-invoice-medicine.html', {
                'invoice_groups': invoice_groups,
                'total_purchases': total_count,
                'company_query': company_query,
                'invoice_query': invoice_query,
                'editing_pk': purchase.pk,
                'edit_errors': edit_errors,
                'edit_values': {'quantity': quantity, 'price': price},
            })

        #medicine = purchase.medicine
        # Stock quantity is a running total across ALL invoices — adjusting by
        # the difference is correct regardless of which invoice this is.
        #quantity_diff = new_quantity - purchase.quantity
        #medicine.quantity = max(0, medicine.quantity + quantity_diff)

        # Update THIS purchase's own record — always safe, always scoped to this invoice only.
        purchase.quantity = new_quantity
        purchase.price_per_unit = new_price
        purchase.total_cost = new_quantity * new_price
        purchase.save()

        # Only let the medicine's CURRENT price follow this edit if this purchase
        # is genuinely the most recent one for this medicine. Otherwise, editing
        # an old invoice would incorrectly roll back today's selling price.
        #latest_purchase = Purchase.objects.filter(medicine=medicine).order_by('-purchased_at', '-id').first()
        #if latest_purchase and latest_purchase.pk == purchase.pk:
        #    medicine.price_per_unit = new_price
        return redirect('pharmacy:edit_invoice_medicine')
    
    return redirect('pharmacy:edit_invoice_medicine')

@login_required
def delete_invoice_medicine(request,pk):
    #purchase = get_object_or_404(Purchase, pk=pk)
    if request.method == 'POST':
        purchase = get_object_or_404(Purchase,pk)
        purchase.delete()

    '''if request.method == 'POST':
        medicine = purchase.medicine
        was_latest = False

        latest_purchase = Purchase.objects.filter(medicine=medicine).order_by('-purchased_at', '-id').first()
        if latest_purchase and latest_purchase.pk == purchase.pk:
            was_latest = True

        medicine.quantity = max(0, medicine.quantity - purchase.quantity)
        purchase.delete()

        # If we just deleted the invoice that was setting the current price,
        # fall back to whichever purchase is now the most recent remaining one.
        if was_latest:
            new_latest = Purchase.objects.filter(medicine=medicine).order_by('-purchased_at', '-id').first()
            if new_latest:
                medicine.price_per_unit = new_latest.price_per_unit
            # if no purchases remain at all, leave price_per_unit as-is —
            # nothing better to fall back to.

        medicine.save()'''
    return redirect('pharmacy:edit_invoice_medicine')
     
@login_required
def add_salesman(request):

    if request.method == 'POST':
        salesman_name = request.POST.get('salesman_name', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            salesmen = User.objects.filter(is_superuser=False, is_active=True)
            return render(request, 'pharmacy/add-salesman.html', {
                'salesmen': salesmen,
                'error': f"Username '{username}' already exists. Choose a different one.",
            })

        # Create the salesman as a regular Django user
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=salesman_name,
            is_staff=False,
            is_superuser=False,
        )

        salesmen = User.objects.filter(is_superuser=False, is_active=True)
        return render(request, 'pharmacy/add-salesman.html', {
            'salesmen': salesmen,
            'success': f"Salesman '{salesman_name}' added successfully!",
        })

    salesmen = User.objects.filter(is_superuser=False, is_active=True)
    return render(request, 'pharmacy/add-salesman.html', {
        'salesmen': salesmen,
    })


@login_required
def delete_salesman(request, pk):
    if request.method == 'POST':
        user = get_object_or_404(User, pk=pk)
        user.delete()
    return redirect('pharmacy:add_salesman')

@login_required
def sale_medicines(request):
    if request.method == 'POST':
        should_print = request.POST.get('print','0') == '1'
        total_count = int(request.POST.get('total_count',0))
        discount = float(request.POST.get('discount', 0))
        subtotal = float(request.POST.get('subtotal',0))
        final_price = float(request.POST.get('final_price',0))
        errors = []
        saved_items = [] # ← collect for receipt

        for i in range(total_count):
            name =  request.POST.get(f'sale_{i}_name')
            product_type = request.POST.get(f'sale_{i}_type', '')  # ← read type
            quantity   = int(request.POST.get(f'sale_{i}_quantity', 0))
            price      = float(request.POST.get(f'sale_{i}_price', 0))
            item_total = float(request.POST.get(f'sale_{i}_total', 0))

            if not name or not quantity or not price:
                continue

            quantity   = int(quantity)
            price      = float(price)
            item_total = float(item_total)

            try:
                # ✅ filter by name AND type — handles duplicate names
                if product_type:
                    medicine = Medicine.objects.get(
                        name__iexact=name,
                        product_type__iexact=product_type
                    )
                else:
                    medicine = Medicine.objects.filter(
                        name__iexact=name
                    ).first()
                    if not medicine:
                        errors.append(f"Medicine '{name}' not found.")
                        continue
            except Medicine.DoesNotExist:
                errors.append(f"Medicine '{name}' not found.")
                continue

            if medicine.quantity<quantity:
                errors.append(
                    f"Not enough stock for '{name}.'"
                    f"Available: {medicine.quantity}, Requested: {quantity}"
                )
                continue

            Sale.objects.create(
                    medicine=medicine,
                    salesman=request.user,
                    quantity_sold=quantity,
                    price_per_unit=price,
                    item_total=item_total,
                    subtotal=subtotal,
                    discount=discount,
                    final_price=final_price,
            )

            medicine.quantity -= quantity
            medicine.save()

            # ← collect item for receipt
            saved_items.append({
                'name': name,
                'type': medicine.product_type,
                'qty': quantity,
                'price': price,
                'total': item_total,
            })


        if errors:
            return render(request,'pharmacy/sale-medicine.html',{'errors':errors})

        # ← store receipt in session if print was requested
        if should_print and saved_items:
            current_utc = timezone.now()
            bd_tz = zoneinfo.ZoneInfo("Asia/Dhaka")
            now = timezone.localtime(current_utc, bd_tz)
            request.session['last_receipt'] = {
                'sale_type':   'Retail Sale',
                'invoice_no':  f"INV-{now.strftime('%Y%m%d-%H%M%S')}",
                'sold_at':     now.strftime('%d %b %Y  %I:%M %p'),
                'salesman':    request.user.get_full_name() or request.user.username,
                'buyer':       None,
                'items':       saved_items,
                'subtotal':    subtotal,
                'discount':    discount,
                'final_price': final_price,
            }
            return redirect('pharmacy:receipt')

        return redirect('pharmacy:sale_medicines')
        
    return render(request,'pharmacy/sale-medicine.html')

@login_required
def medicine_search(request):
    query = request.GET.get('q','').strip()
    results = []

    if query:
        medicines = Medicine.objects.filter(name__icontains = query).values('name','product_type','quantity','price_per_unit')[:8]

        for m in medicines:
            results.append({
                'name': m['name'],
                'product_type': m['product_type'],
                'quantity': m['quantity'],
                'price': float(m['price_per_unit']),
            })
    return JsonResponse({'results': results})

from django.http import JsonResponse

@login_required
def get_medicine_price(request):
    name = request.GET.get('name', '').strip()
    product_type = request.GET.get('type', '').strip()
    try:
        if product_type:
            medicine = Medicine.objects.get(
                name__iexact=name,
                product_type__iexact=product_type
            )
        else:
            # fallback — if no type sent, get the first match
            medicine = Medicine.objects.filter(
                name__iexact=name).first()
            if not medicine:
                return JsonResponse({'found': False})
        return JsonResponse({
            'found': True,
            'price': float(medicine.price_per_unit),
            'stock': medicine.quantity,
            'product_type': medicine.product_type,
        })
    except Medicine.DoesNotExist:
        return JsonResponse({'found': False})
    except Medicine.MultipleObjectsReturned:
        # Should not happen now, but safe fallback
        medicine = Medicine.objects.filter(
            name__iexact=name
        ).first()
        return JsonResponse({
            'found':        True,
            'price':        float(medicine.price_per_unit),
            'stock':        medicine.quantity,
            'product_type': medicine.product_type,
        })

@login_required
def wholesale(request):
    if request.method == 'POST':
        should_print = request.POST.get('print','0') == '1'
        buyer_name = request.POST.get('buyer_name','').strip()
        total_count = int(request.POST.get('total_count',0))
        discount = float(request.POST.get('discount',0))
        subtotal = float(request.POST.get('subtotal',0))
        final_price = float(request.POST.get('final_price',0))
        errors = []
        saved_items = [] # ← collect for receipt

        # Buyer name is required
        if not buyer_name:
            return render(request,'pharmacy/wholesale.html',{'errors': ['Buyer name is required']})

        for i in range(total_count):
            name = request.POST.get(f'sale_{i}_name')
            product_type = request.POST.get(f'sale_{i}_type', '')  # ← read type
            quantity = request.POST.get(f'sale_{i}_quantity')
            price = request.POST.get(f'sale_{i}_price')
            item_total = request.POST.get(f'sale_{i}_total')

            if not name or not quantity or not price:
                continue

            quantity = int(quantity)
            price = float(price)
            item_total = float(item_total)

            try:
                # ✅ filter by name AND type — handles duplicate names
                if product_type:
                    medicine = Medicine.objects.get(
                        name__iexact=name,
                        product_type__iexact=product_type
                    )
                else:
                    medicine = Medicine.objects.filter(
                        name__iexact=name
                    ).first()
                    if not medicine:
                        errors.append(f"Medicine '{name}' not found.")
                        continue
            except Medicine.DoesNotExist:
                errors.append(f"Medicine '{name}' not found.")
                continue

            if medicine.quantity<quantity:
                errors.append(
                    f"Not enough stock for '{name}.'"
                    f"Available: {medicine.quantity}, Requested: {quantity}"
                )
                continue

            Wholesale.objects.create(
                buyer_name = buyer_name,
                medicine=medicine,
                salesman=request.user,
                quantity_sold=quantity,
                price_per_unit=price,
                item_total=item_total,
                subtotal=subtotal,
                discount=discount,
                final_price=final_price,
            )
            
            medicine.quantity -= quantity
            medicine.save()

            # ← collect item for receipt
            saved_items.append({
                'name': name,
                'type': medicine.product_type,
                'qty': quantity,
                'price': price,
                'total': item_total,
            })

        if errors:
            return render(request,'pharmacy/wholesale.html', {'errors': errors})

        # ← store receipt in session if print was requested
        if should_print and saved_items:
            current_utc = timezone.now()
            bd_tz = zoneinfo.ZoneInfo("Asia/Dhaka")
            now = timezone.localtime(current_utc, bd_tz)
            request.session['last_receipt'] = {
                'sale_type':   'Wholesale',
                'invoice_no':  f"WHL-{now.strftime('%Y%m%d-%H%M%S')}",
                'sold_at':     now.strftime('%d %b %Y  %I:%M %p'),
                'salesman':    request.user.get_full_name() or request.user.username,
                'buyer':       buyer_name,
                'items':       saved_items,
                'subtotal':    subtotal,
                'discount':    discount,
                'final_price': final_price,
            }
            return redirect('pharmacy:receipt')
        
        return redirect('pharmacy:wholesale')

    return render(request,'pharmacy/wholesale.html')


@login_required
def get_wholesale_price(request):
    name = request.GET.get('name', '').strip()
    product_type = request.GET.get('type', '').strip()
    try:
       # ✅ filter by both name AND type to get exactly one result
        if product_type:
            medicine = Medicine.objects.get(
                name__iexact=name,
                product_type__iexact=product_type
            )
        else:
            # fallback — if no type sent, get the first match
            medicine = Medicine.objects.filter(
                name__iexact=name).first()
            if not medicine:
                return JsonResponse({'found': False})
        return JsonResponse({
            'found': True,
            'price': float(medicine.price_per_unit),
            'stock': medicine.quantity,
            'product_type': medicine.product_type,
        })
    except Medicine.DoesNotExist:
        return JsonResponse({'found': False})
    except Medicine.MultipleObjectsReturned:
        # Should not happen now, but safe fallback
        medicine = Medicine.objects.filter(
            name__iexact=name
        ).first()
        return JsonResponse({
            'found':        True,
            'price':        float(medicine.price_per_unit),
            'stock':        medicine.quantity,
            'product_type': medicine.product_type,
        })
    
@login_required
def update_medicine(request):
    if request.method == 'POST':
        total_count = int(request.POST.get('total_count',0))
        
        for i in range(total_count):
            name = request.POST.get(f'medicine_{i}_name')
            company = request.POST.get(f'medicine_{i}_company')
            type_ = request.POST.get(f'medicine_{i}_type')
            quantity = request.POST.get(f'medicine_{i}_quantity')
            price = request.POST.get(f'medicine_{i}_price')
            invoice_number = request.POST.get(f'medicine_{i}_invoice', '')  # ← add
            total_price = request.POST.get(f'medicine_{i}_total_price')
            total_dis_price = request.POST.get(f'medicine_{i}_total_dis_price')
        
            if name and type_ and quantity and price:
                quantity= int(quantity)
                price =  float(price)
                total_price = float(total_price)
                total_dis_price = float(total_price)

                # Check for an existing medicine with the same name + type
                existing = Medicine.objects.filter(
                    name__iexact=name,
                    product_type__iexact=type_
                ).order_by('id').first()

                if existing:
                    # Restock: add to existing quantity, update price to the new one
                    existing.quantity += quantity
                    existing.price_per_unit = price
                    existing.total_price = (existing.total_price or float('0')) + total_price
                    if company:
                        existing.company = company
                    if invoice_number:
                        existing.invoice_number = invoice_number
                    existing.save()
                    medicine = existing
                else:
                    medicine = Medicine.objects.create(
                        name=name,
                        company=company, 
                        product_type=type_,
                        quantity=int(quantity),
                        price_per_unit=float(price),
                        total_price =float(total_price),
                        total_dis_price = float(total_dis_price),
                    )
        
                Purchase.objects.create(
                    medicine=medicine,
                    company=company or '',
                    quantity=quantity,
                    price_per_unit=price,
                    total_cost=quantity * price,
                    total_dis_price = float(total_dis_price),
                    invoice_number = invoice_number,
                    added_by=request.user,
                )
                if company and invoice_number:
                    company_obj = Company.objects.filter(company__iexact=company).first()
                    if not company_obj:
                        company_obj = Company.objects.create(company=company)

                    invoice_exists = Invoice.objects.filter(
                        company=company_obj,
                        invoice_number__iexact=invoice_number
                    ).exists()
                    if not invoice_exists:
                        Invoice.objects.create(company=company_obj, invoice_number=invoice_number)
        return redirect('pharmacy:update_medicine')
                     
    return render(request,'pharmacy/update-medicine.html')

@login_required
def receipt(request):
    data = request.session.pop('last_receipt',None)
    if not data:
        return redirect('pharmacy:sale_medicines')
    return render(request, 'pharmacy/receipt.html', {'receipt': data})

@login_required
def medicine_list(request):
    search = request.GET.get('search','').strip()
    company = request.GET.get('company','').strip()

    medicines = Medicine.objects.all()

    if search:
        medicines = medicines.filter(name__icontains=search)

    if company:
        medicines = medicines.filter(company__iexact=company)

    # Get unique company names for the dropdown filter
    companies = Medicine.objects.values_list(
        'company', flat=True
    ).distinct().order_by('company')

    return render(request, 'pharmacy/medicine-list.html', {
        'medicines': medicines,
        'companies': companies,
        'search': search,
        'selected_company': company,
    })

@login_required
def medicine_suggestions(request):
    query = request.GET.get('q', '').strip()
    suggestions = []

    if query:
        matches = Medicine.objects.filter(
            name__icontains=query
        ).values_list('name', flat=True).distinct()[:8]
        suggestions = list(matches)

    return JsonResponse({'suggestions': suggestions})

@login_required
def sales_report(request):
    tab  = request.GET.get('tab','today')
    today = timezone.localdate()

    sales_data = None
    wholesale_data = None
    purchase_data = None
    weekly_data  = None
    monthly_data = None
    yearly_data = None

    weekly_totals  = None
    monthly_totals = None
    yearly_totals  = None

    sale_total_today      = 0
    wholesale_total_today = 0
    purchase_total_today  = 0

    # Options for dropdowns
    month_choices = [{'num':i,'name':calendar.month_name[i]} for i in range(1,13)]
    #Years list: current year down 5 years
    year_choices = list(range(today.year,today.year-6,-1))

    # Parse selected month and year
    try:
        selected_month = int(request.GET.get('month', today.month))
    except (ValueError, TypeError):
        selected_month = today.month

    try:
        selected_year = int(request.GET.get('year', today.year))
    except (ValueError, TypeError):
        selected_year = today.year

    if tab == 'today':
        sales_data = Sale.objects.filter(sold_at__date=today).select_related('medicine','salesman').order_by('sold_at')
        wholesale_data = Wholesale.objects.filter(sold_at__date=today).select_related('medicine','salesman').order_by('sold_at')
        purchase_data = Purchase.objects.filter(purchased_at__date=today).select_related('medicine','added_by').order_by('purchased_at')

        sale_total_today = float(sales_data.aggregate(t=Sum('final_price'))['t'] or 0)
        wholesale_total_today = float(wholesale_data.aggregate(t=Sum('final_price'))['t'] or 0)
        purchase_total_today = float(purchase_data.aggregate(t=Sum('total_cost'))['t'] or 0)

    elif tab == 'weekly':
        # Find most recent Saturday
        # Python weekday(): Mon=0 Tue=1 Wed=2 Thu=3 Fri=4 Sat=5 Sun=6
        days_since_saturday = (today.weekday()-5)%7
        week_start = today - timedelta(days=days_since_saturday)

        day_names = [
            'Saturday', 'Sunday', 'Monday',
            'Tuesday', 'Wednesday', 'Thursday', 'Friday'
        ]

        weekly_data = []
        tot_s_qty = tot_w_qty = tot_p_qty = 0
        tot_s_amt = tot_w_amt = tot_p_amt = 0.0
        for i in range(7):
            day = week_start+ timedelta(days=i)

            day_sales = Sale.objects.filter(sold_at__date=day).aggregate(amount=Sum('final_price'),qty=Sum('quantity_sold'))
            day_wholesale = Wholesale.objects.filter(sold_at__date=day).aggregate(amount=Sum('final_price'),qty=Sum('quantity_sold'))
            day_purchases = Purchase.objects.filter(purchased_at__date=day).aggregate(amount=Sum('total_cost'),qty=Sum('quantity'))

            sale_amt = float(day_sales['amount'] or 0)
            wholesale_amt = float(day_wholesale['amount'] or 0)
            purchase_amt = float(day_purchases['amount'] or 0)

            s_qty = day_sales['qty'] or 0
            w_qty = day_wholesale['qty'] or 0
            p_qty = day_purchases['qty'] or 0

            s_amt = float(day_sales['amount'] or 0)
            w_amt = float(day_wholesale['amount'] or 0)
            p_amt = float(day_purchases['amount'] or 0)

            tot_s_qty += s_qty
            tot_w_qty += w_qty
            tot_p_qty += p_qty
            tot_s_amt += s_amt
            tot_w_amt += w_amt
            tot_p_amt += p_amt

            weekly_data.append({
                'day_name':         day_names[i],
                'label':            day_names[i],
                'date':             day,
                'sale_qty':         day_sales['qty'] or 0,
                'sale_amount':      sale_amt,
                'wholesale_qty':    day_wholesale['qty'] or 0,
                'wholesale_amount': wholesale_amt,
                'purchase_qty':     day_purchases['qty'] or 0,
                'purchase_amount':  purchase_amt,
                'net':              (sale_amt + wholesale_amt) - purchase_amt,
                'is_today':         day == today,
            })

        weekly_totals = {
            'sale_qty': tot_s_qty,
            'sale_amount': tot_s_amt,
            'wholesale_qty': tot_w_qty,
            'wholesale_amount': tot_w_amt,
            'purchase_qty': tot_p_qty,
            'purchase_amount': tot_p_amt,
            'net': (tot_s_amt + tot_w_amt) - tot_p_amt,
        }

    elif tab == 'monthly':
        days_in_month = calendar.monthrange(selected_year, selected_month)[1]
        monthly_data = []
        tot_s_qty = tot_w_qty = tot_p_qty = 0
        tot_s_amt = tot_w_amt = tot_p_amt = 0.0
        for day_num in range(1,days_in_month+1):
            day = date(selected_year,selected_month,day_num)

            day_sales = Sale.objects.filter(sold_at__date=day).aggregate(amount=Sum('final_price'),
                                                                                     qty=Sum('quantity_sold'))
            day_wholesale = Wholesale.objects.filter(sold_at__date=day).aggregate(amount=Sum('final_price'),
                                                                                     qty=Sum('quantity_sold'))
            day_purchases = Purchase.objects.filter(purchased_at__date=day).aggregate(amount=Sum('total_cost'),
                                                                                     qty=Sum('quantity'))

            sale_amt = float(day_sales['amount'] or 0)
            wholesale_amt = float(day_wholesale['amount'] or 0)
            purchase_amt = float(day_purchases['amount'] or 0)

            s_qty = day_sales['qty'] or 0
            w_qty = day_wholesale['qty'] or 0
            p_qty = day_purchases['qty'] or 0

            s_amt = float(day_sales['amount'] or 0)
            w_amt = float(day_wholesale['amount'] or 0)
            p_amt = float(day_purchases['amount'] or 0)

            tot_s_qty += s_qty
            tot_w_qty += w_qty
            tot_p_qty += p_qty
            tot_s_amt += s_amt
            tot_w_amt += w_amt
            tot_p_amt += p_amt

            monthly_data.append({
                'label':            day.strftime('%d %b'),
                'date':             day,
                'sale_qty':         day_sales['qty'] or 0,
                'sale_amount':      sale_amt,
                'wholesale_qty':    day_wholesale['qty'] or 0,
                'wholesale_amount': wholesale_amt,
                'purchase_qty':     day_purchases['qty'] or 0,
                'purchase_amount':  purchase_amt,
                'net':              (sale_amt + wholesale_amt) - purchase_amt,
                'is_today':         day == today,
            })

        monthly_totals = {
            'sale_qty': tot_s_qty,
            'sale_amount': tot_s_amt,
            'wholesale_qty': tot_w_qty,
            'wholesale_amount': tot_w_amt,
            'purchase_qty': tot_p_qty,
            'purchase_amount': tot_p_amt,
            'net': (tot_s_amt + tot_w_amt) - tot_p_amt,
        }

    elif tab == 'yearly':
        """month_names = [
            'January', 'February', 'March', 'April',
            'May', 'June', 'July', 'August',
            'September', 'October', 'November', 'December'
        ]"""
        yearly_data=[]
        tot_s_qty = tot_w_qty = tot_p_qty = 0
        tot_s_amt = tot_w_amt = tot_p_amt = 0.0

        for month_num in range(1,13):
            month_sales = Sale.objects.filter(sold_at__year=selected_year,sold_at__month=month_num ).aggregate(amount=Sum('final_price'),
                                                                                                 qty=Sum('quantity_sold'))
            month_wholesale = Wholesale.objects.filter(sold_at__year=selected_year,sold_at__month=month_num).aggregate(amount=Sum('final_price'),
                                                                                                         qty=Sum('quantity_sold'))
            month_purchases = Purchase.objects.filter(purchased_at__year=selected_year,purchased_at__month=month_num).aggregate(amount=Sum('total_cost'),
                                                                                                                    qty=Sum('quantity'))

            sale_amt = float(month_sales['amount'] or 0)
            wholesale_amt = float(month_wholesale['amount'] or 0)
            purchase_amt = float(month_purchases['amount'] or 0)

            s_qty = month_sales['qty'] or 0
            w_qty = month_wholesale['qty'] or 0
            p_qty = month_purchases['qty'] or 0

            s_amt = float(month_sales['amount'] or 0)
            w_amt = float(month_wholesale['amount'] or 0)
            p_amt = float(month_purchases['amount'] or 0)

            tot_s_qty += s_qty
            tot_w_qty += w_qty
            tot_p_qty += p_qty
            tot_s_amt += s_amt
            tot_w_amt += w_amt
            tot_p_amt += p_amt

            yearly_data.append({
                'label':            calendar.month_name[month_num],
                'sale_qty':         month_sales['qty'] or 0,
                'sale_amount':      sale_amt,
                'wholesale_qty':    month_wholesale['qty'] or 0,
                'wholesale_amount': wholesale_amt,
                'purchase_qty':     month_purchases['qty'] or 0,
                'purchase_amount':  purchase_amt,
                'net':              (sale_amt + wholesale_amt) - purchase_amt,
                'is_current':        month_num == today.month,
            })

        yearly_totals = {
            'sale_qty': tot_s_qty,
            'sale_amount': tot_s_amt,
            'wholesale_qty': tot_w_qty,
            'wholesale_amount': tot_w_amt,
            'purchase_qty': tot_p_qty,
            'purchase_amount': tot_p_amt,
            'net': (tot_s_amt + tot_w_amt) - tot_p_amt,
        }

    context = {
        'tab':                    tab,
        'today':                  today,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'month_choices': month_choices,
        'year_choices': year_choices,
        'sales_data':             sales_data,
        'wholesale_data':         wholesale_data,
        'purchase_data':          purchase_data,
        'weekly_data':            weekly_data,
        'monthly_data':           monthly_data,
        'yearly_data':            yearly_data,
        'weekly_totals':          weekly_totals,    # ← add
        'monthly_totals':         monthly_totals,   # ← add
        'yearly_totals':          yearly_totals,    # ← add
        'sale_total_today':       sale_total_today,
        'wholesale_total_today':  wholesale_total_today,
        'purchase_total_today':   purchase_total_today,
    }
    return render(request,'pharmacy/sales-report.html',context)

@login_required
def sales_history(request):
    # Read selected date from URL — default to today
    date_str      = request.GET.get('date', '')
    selected_date = None
    sales         = None
    wholesale     = None
    pro_sales     = None

    sale_total      = 0
    wholesale_total = 0
    pro_total       = 0

    if date_str:
        try:
            # Parse the date string from the date picker (format: YYYY-MM-DD)
            selected_date = date.fromisoformat(date_str)

            sales = Sale.objects.filter(
                sold_at__date=selected_date
            ).select_related('medicine', 'salesman').order_by('sold_at')

            wholesale = Wholesale.objects.filter(
                sold_at__date=selected_date
            ).select_related('medicine', 'salesman').order_by('sold_at')
            pro_sales = ProCustomerSale.objects.filter(
                sold_at__date=selected_date
            ).select_related('medicine', 'salesman', 'customer').order_by('sold_at')

            sale_total = float(
                sales.aggregate(t=Sum('final_price'))['t'] or 0
            )
            wholesale_total = float(
                wholesale.aggregate(t=Sum('final_price'))['t'] or 0
            )
            pro_total = float(
                pro_sales.aggregate(t=Sum('final_price'))['t'] or 0
            )
        except ValueError:
            selected_date = None

    context = {
    'selected_date':  selected_date,
    'date_str':       date_str,
    'sales':          sales,
    'wholesale':      wholesale,
    'pro_sales':      pro_sales,
    'sale_total':     sale_total,
    'wholesale_total': wholesale_total,
    'pro_total':      pro_total,
    'grand_total':    sale_total + wholesale_total+pro_total,
    }
    return render(request,'pharmacy/sales-history.html',context)
        

@login_required
def pro_customer(request):
    error = None
    success = None
    if request.method == 'POST':
        name = request.POST.get('customer_name','').strip()
        phone = request.POST.get('phone_number','').strip()

        if not name or not phone:
            error = 'Both name and phone number are required.'

        elif len(phone) !=11:
            error = f"Phone number must be exactly 11 digits."

        elif ProCustomer.objects.filter(phone_number = phone).exists():
            error = f"Phone number '{phone}' is already registered."

        else:
            ProCustomer.objects.create(
                name=name,
                phone_number=phone,
            )
            success = f"Pro customer '{name}' added successfully."
    procustomers = ProCustomer.objects.all().order_by('-created_at')

    return render(request, 'pharmacy/pro-customer.html', {
            'procustomers': procustomers,
            'errors':       error,
            'success' :     success, 
        })

@login_required
def delete_pro_customer(request,pk):
    if request.method == 'POST':
        customer = get_object_or_404(ProCustomer, pk=pk)
        customer.delete()
    return redirect('pharmacy:pro_customer')

@login_required
def get_pro_customers(request):
    query = request.GET.get('q','').strip()
    customers = []
    if query:
        matches = ProCustomer.objects.filter(name__icontains=query).values('id','name','phone_number')[:8]
        customers = list(matches)
    return JsonResponse({'customers':customers})

@login_required
def get_pro_customer_price(request):
    name = request.GET.get('name','').strip()
    product_type = request.GET.get('type', '').strip()
    try:
        if product_type:
            medicine = Medicine.objects.get(
                name__iexact=name,
                product_type__iexact=product_type
            )
        else:
            # fallback — if no type sent, get the first match
            medicine = Medicine.objects.filter(
                name__iexact=name).first()
            if not medicine:
                return JsonResponse({'found': False})
        return JsonResponse({
            'found':        True,
            'price':        float(medicine.price_per_unit),
            'stock':        medicine.quantity,
            'product_type': medicine.product_type,
        })

    except Medicine.DoesNotExist:
        return JsonResponse({'found': False})
    except Medicine.MultipleObjectsReturned:
        # Should not happen now, but safe fallback
        medicine = Medicine.objects.filter(
            name__iexact=name
        ).first()
        return JsonResponse({
            'found':        True,
            'price':        float(medicine.price_per_unit),
            'stock':        medicine.quantity,
            'product_type': medicine.product_type,
        })

@login_required
def pro_customer_sale(request):
    if request.method == 'POST':
        print("=== POST received ===")
        should_print = request.POST.get('print', '0') == '1'
        customer_id = request.POST.get('customer_id')
        total_count = int(request.POST.get('total_count',0))
        print(f"customer_id={customer_id}, total_count={total_count}")
        discount = float(request.POST.get('discount',0))
        subtotal = float(request.POST.get('subtotal',0))
        final_price = float(request.POST.get('final_price',0))
        errors = []
        saved_items  = []

        #Validate customer_id
        if not customer_id:
            errors.append('Please select a pro customer')
            procustomers = ProCustomer.objects.all().order_by('name')
            return render(request,'pharmacy/pro-customer-sale.html',{
                'errors': errors,
                'procustomers': procustomers,
            })

        try:
            customer = ProCustomer.objects.get(pk=customer_id)
        except ProCustomer.DoesNotExist:
            errors.append('Selected customer not found.')
            procustomers = ProCustomer.objects.all().order_by('name')
            return render(request,'pharmacy/pro-customer-sale.html',{
                'errors': errors,
                'procustomers': procustomers,
            })
        for i in range(total_count):
            name = request.POST.get(f'sale_{i}_name')
            product_type = request.POST.get(f'sale_{i}_type', '')  # ← read type
            quantity = request.POST.get(f'sale_{i}_quantity')
            price = request.POST.get(f'sale_{i}_price')
            item_total = request.POST.get(f'sale_{i}_total')
        
            print(f"Row {i}: name={name}, qty={quantity}, price={price}, total={item_total}")

            if not name or not quantity or not price:
                continue
        
            quantity = int(quantity)
            price = float(price)
            item_total = float(item_total)
        
            try:
                # ✅ filter by name AND type — handles duplicate names
                if product_type:
                    medicine = Medicine.objects.get(
                        name__iexact=name,
                        product_type__iexact=product_type
                    )
                else:
                    medicine = Medicine.objects.filter(
                        name__iexact=name
                    ).first()
                    if not medicine:
                        errors.append(f"Medicine '{name}' not found.")
                        continue
            except Medicine.DoesNotExist:
                errors.append(f"Medicine '{name}' not found.")
                continue
        
            if medicine.quantity<quantity:
                errors.append(
                    f"Not enough stock for '{name}.'"
                    f"Available: {medicine.quantity}, Requested: {quantity}"
                )
                continue
            # Save to ProCustomerSale — separate from Sale and Wholesale
            try:
                sale = ProCustomerSale.objects.create(
                    customer=customer,
                    medicine=medicine,
                    salesman=request.user,
                    quantity_sold=quantity,
                    price_per_unit=price,
                    item_total=item_total,
                    subtotal=subtotal,
                    discount=discount,
                    final_price=final_price,
                )
                print(f"CREATED sale pk={sale.pk}")
            except Exception as e:
                print(f"CREATE FAILED: {e}")
                errors.append(f"Could not save sale for {name}: {e}")
                continue
            medicine.quantity -= quantity
            medicine.save()
            print(f"Medicine {medicine.name} qty now {medicine.quantity}")

            saved_items.append({
                'name':  name,
                'type':  medicine.product_type,
                'qty':   quantity,
                'price': price,
                'total': item_total,
            })
            
        if errors:
            procustomers = ProCustomer.objects.all().order_by('name')
            return render(request,'pharmacy/pro-customer-sale.html',{
                'errors': errors,
                'procustomers': procustomers,
            })

        if should_print and saved_items:
            current_utc = timezone.now()
            bd_tz = zoneinfo.ZoneInfo("Asia/Dhaka")
            now = timezone.localtime(current_utc, bd_tz)
            request.session['last_receipt'] = {
                'sale_type':      'Pro Customer Sale',
                'invoice_no':     f"PRO-{now.strftime('%Y%m%d-%H%M%S')}",
                'sold_at':        now.strftime('%d %b %Y  %I:%M %p'),
                'salesman':       request.user.get_full_name() or request.user.username,
                'buyer':          customer.name,
                'buyer_phone':    customer.phone_number,
                'items':          saved_items,
                'subtotal':       subtotal,
                'discount':       discount,
                'final_price':    final_price,
            }
            return redirect('pharmacy:receipt')

        return redirect('pharmacy:pro_customer_sale')
        
    procustomers = ProCustomer.objects.all().order_by('name')                  
    return render(request,'pharmacy/pro-customer-sale.html',{
        'procustomers': procustomers,
    })

@login_required
def pro_customer_report(request):
    today = timezone.localdate()

    # Dropdown options
    month_choices = [{'num': i, 'name': calendar.month_name[i]} for i in range(1, 13)]
    year_choices = list(range(today.year, today.year - 6, -1))

    # Read selected month & year from GET parameters (default to current)
    try:
        selected_month = int(request.GET.get('month', today.month))
    except (ValueError, TypeError):
        selected_month = today.month

    try:
        selected_year = int(request.GET.get('year', today.year))
    except (ValueError, TypeError):
        selected_year = today.year

    # Filter condition for the specific month and year
    monthly_filter = Q(
        orders__sold_at__year=selected_year,
        orders__sold_at__month=selected_month,
    )

    # Get every pro customer and annotate with their yearly totals
    customers = ProCustomer.objects.annotate(

        # Total units sold to this customer this year
        total_qty = Sum(
            'orders__quantity_sold',
            filter=monthly_filter
        ),

        # Total revenue before discount
        total_subtotal = Sum(
            'orders__subtotal',
            filter=monthly_filter
        ),

         # Total discount given
         total_discount = Sum(
            'orders__discount',
            filter=monthly_filter
        ),

        # Net amount actually paid — this is what we display
        net_sale = Sum(
            'orders__final_price',
            filter=monthly_filter
        ),

        # Count of individual transactions
        order_count = Count(
            'orders',
            filter=monthly_filter,
            distinct=True
        ),

        # Last purchase date
        last_order=Max('orders__sold_at',filter=monthly_filter),
    ).order_by('-net_sale')

    # Convert Decimal to float and handle None for customers with no orders
    customer_data = []
    for c in customers:
        net = float(c.net_sale or 0)
        customer_data.append({
            'id': c.pk,
            'name': c.name,
            'phone_number': c.phone_number,
            'registered_on': c.created_at,
            'order_count': c.order_count or 0,
            'total_quantity': c.total_qty or 0,
            'total_discount': float(c.total_discount or 0),
            'net_sale': net,
            'last_order': c.last_order,
            #'tier': get_tier(net), 
        })
    # Grand total across all customers
    grand_total = sum(c['net_sale'] for c in customer_data)
    total_customers = len(customer_data)
    active_customers = sum(1 for c in customer_data if c['net_sale'] > 0)
    inactive_customers = max(0, total_customers - active_customers)

    context = {
        'customer_data': customer_data,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'month_name': calendar.month_name[selected_month],
        'month_choices': month_choices,
        'year_choices': year_choices,
        'grand_total': grand_total,
        'total_customers': total_customers,
        'active_customers': active_customers,
        'inactive_customers': inactive_customers,
    }    

    return render(request,'pharmacy/pro-customer-report.html',context)

"""def get_tier(net_sale):
    #Assign a tier label based on yearly spend.
    if net_sale >= 50000:
        return {'label': 'Platinum', 'color': '#7C3AED'}
    elif net_sale >= 20000:
        return {'label': 'Gold',     'color': '#F2A93B'}
    elif net_sale >= 5000:
        return {'label': 'Silver',   'color': '#5C6F6C'}
    elif net_sale > 0:
        return {'label': 'Bronze',   'color': '#C2855A'}
    else:
        return {'label': 'Inactive', 'color': '#94A6A3'}"""