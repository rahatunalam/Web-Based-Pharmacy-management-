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
from .models import Medicine,Sale,Wholesale,Purchase,ProCustomer,ProCustomerSale
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
            total_price = request.POST.get(f'medicine_{i}_total_price')

            if name and type_ and quantity and price:
                quantity= int(quantity)
                price =  float(price)
                 
                medicine = Medicine.objects.create(
                    name=name,
                    company=company, 
                    product_type=type_,
                    quantity=int(quantity),
                    price_per_unit=float(price),
                    total_price =float(total_price)
                )

                Purchase.objects.create(
                    medicine=medicine,
                    company=company or '',
                    quantity=quantity,
                    price_per_unit=price,
                    total_cost=quantity * price,
                    added_by=request.user,
                )
        return redirect('pharmacy:add_medicine')
                 
    return render(request,'pharmacy/add-medicine.html')

@login_required
def s_add_medicine(request):

    if request.method == 'POST':
        total_count = int(request.POST.get('total_count',0))

        for i in range(total_count):
            name = request.POST.get(f'medicine_{i}_name')
            company = request.POST.get(f'medicine_{i}_company')
            type_ = request.POST.get(f'medicine_{i}_type')
            quantity = request.POST.get(f'medicine_{i}_quantity')
            price = request.POST.get(f'medicine_{i}_price')
            total_price = request.POST.get(f'medicine_{i}_total_price')

            if name and type_ and quantity and price:
                 Medicine.objects.create(
                    name=name,
                    company=company, 
                    product_type=type_,
                    quantity=int(quantity),
                    price_per_unit=float(price),
                    total_price =float(total_price)
                )
        return redirect('pharmacy:s_add_medicine')
                 
    return render(request,'pharmacy/s-add-medicine.html')



@login_required
def edit_medicine(request):
    
    search = request.GET.get('search', '')
    medicines = None

    if search:
        medicines = Medicine.objects.filter(name__icontains=search)
    else:
        medicines = Medicine.objects.all().order_by('name')

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
        try:
            float(price)
        except(ValueError,TypeError):
            errors.append('Price must be a vlaid number.')

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
        medicine.quantity = int(quantity)
        medicine.price_per_unit = float(price)
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
        medicine.delete()
    return redirect('pharmacy:delete_medicine')

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
        total_count = int(request.POST.get('total_count',0))
        discount = float(request.POST.get('discount', 0))
        subtotal = float(request.POST.get('subtotal',0))
        final_price = float(request.POST.get('final_price',0))
        errors = []

        for i in range(total_count):
            name =  request.POST.get(f'sale_{i}_name')
            quantity   = int(request.POST.get(f'sale_{i}_quantity', 0))
            price      = float(request.POST.get(f'sale_{i}_price', 0))
            item_total = float(request.POST.get(f'sale_{i}_total', 0))

            try:
                medicine = Medicine.objects.get(name__iexact=name)
            except:
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


        if errors:
            return render(request,'pharmacy/sale-medicine.html',{'errors':errors})

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
    try:
        medicine = Medicine.objects.get(name__iexact=name)
        return JsonResponse({
            'found': True,
            'price': float(medicine.price_per_unit),
            'stock': medicine.quantity,
            'product_type': medicine.product_type,
        })
    except Medicine.DoesNotExist:
        return JsonResponse({'found': False})

@login_required
def wholesale(request):
    if request.method == 'POST':
        buyer_name = request.POST.get('buyer_name','').strip()
        total_count = int(request.POST.get('total_count',0))
        discount = float(request.POST.get('discount',0))
        subtotal = float(request.POST.get('subtotal',0))
        final_price = float(request.POST.get('final_price',0))
        errors = []

        # Buyer name is required
        if not buyer_name:
            return render(request,'pharmacy/wholesale.html',{'errors': ['Buyer name is required']})

        for i in range(total_count):
            name = request.POST.get(f'sale_{i}_name')
            quantity = request.POST.get(f'sale_{i}_quantity')
            price = request.POST.get(f'sale_{i}_price')
            item_total = request.POST.get(f'sale_{i}_total')

            if not name or not quantity or not price:
                continue

            quantity = int(quantity)
            price = float(price)
            item_total = float(item_total)

            try:
                medicine = Medicine.objects.get(name__iexact=name)
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

        if errors:
            return render(request,'pharmacy/wholesale.html', {'errors': errors})

        return redirect('pharmacy:wholesale')

    return render(request,'pharmacy/wholesale.html')


@login_required
def get_wholesale_price(request):
    name = request.GET.get('name', '').strip()
    try:
        medicine = Medicine.objects.get(name__iexact=name)
        return JsonResponse({
            'found': True,
            'price': float(medicine.price_per_unit),
            'stock': medicine.quantity,
            'product_type': medicine.product_type,
        })
    except Medicine.DoesNotExist:
        return JsonResponse({'found': False})
    
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
                total_price = request.POST.get(f'medicine_{i}_total_price')
    
                if name and type_ and quantity and price:
                     Medicine.objects.create(
                        name=name,
                        company=company, 
                        product_type=type_,
                        quantity=int(quantity),
                        price_per_unit=float(price),
                        total_price =float(total_price)
                    )
            return redirect('pharmacy:update_medicine')
                     
    return render(request,'pharmacy/update-medicine.html')

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

    sale_total_today      = 0
    wholesale_total_today = 0
    purchase_total_today  = 0

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
        for i in range(7):
            day = week_start+ timedelta(days=i)

            day_sales = Sale.objects.filter(sold_at__date=day).aggregate(amount=Sum('final_price'),qty=Sum('quantity_sold'))
            day_wholesale = Wholesale.objects.filter(sold_at__date=day).aggregate(amount=Sum('final_price'),qty=Sum('quantity_sold'))
            day_purchases = Purchase.objects.filter(purchased_at__date=day).aggregate(amount=Sum('total_cost'),qty=Sum('quantity'))

            sale_amt = float(day_sales['amount'] or 0)
            wholesale_amt = float(day_wholesale['amount'] or 0)
            purchase_amt = float(day_purchases['amount'] or 0)

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

    elif tab == 'monthly':
        days_in_month = calendar.monthrange(today.year,today.month)[1]
        monthly_data = []
        for day_num in range(1,days_in_month+1):
            day = date(today.year,today.month,day_num)

            day_sales = Sale.objects.filter(sold_at__date=day).aggregate(amount=Sum('final_price'),
                                                                                     qty=Sum('quantity_sold'))
            day_wholesale = Wholesale.objects.filter(sold_at__date=day).aggregate(amount=Sum('final_price'),
                                                                                     qty=Sum('quantity_sold'))
            day_purchases = Purchase.objects.filter(purchased_at__date=day).aggregate(amount=Sum('total_cost'),
                                                                                     qty=Sum('quantity'))

            sale_amt = float(day_sales['amount'] or 0)
            wholesale_amt = float(day_wholesale['amount'] or 0)
            purchase_amt = float(day_purchases['amount'] or 0)

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

    elif tab == 'yearly':
        month_names = [
            'January', 'February', 'March', 'April',
            'May', 'June', 'July', 'August',
            'September', 'October', 'November', 'December'
        ]
        yearly_data=[]

        for month_num in range(1,13):
            month_sales = Sale.objects.filter(sold_at__year=today.year,sold_at__month=month_num ).aggregate(amount=Sum('final_price'),
                                                                                                 qty=Sum('quantity_sold'))
            month_wholesale = Wholesale.objects.filter(sold_at__year=today.year,sold_at__month=month_num).aggregate(amount=Sum('final_price'),
                                                                                                         qty=Sum('quantity_sold'))
            month_purchases = Purchase.objects.filter(purchased_at__year=today.year,purchased_at__month=month_num).aggregate(amount=Sum('total_cost'),
                                                                                                                    qty=Sum('quantity'))

            sale_amt = float(month_sales['amount'] or 0)
            wholesale_amt = float(month_wholesale['amount'] or 0)
            purchase_amt = float(month_purchases['amount'] or 0)

            yearly_data.append({
                'label':            month_names[month_num - 1],
                'sale_qty':         month_sales['qty'] or 0,
                'sale_amount':      sale_amt,
                'wholesale_qty':    month_wholesale['qty'] or 0,
                'wholesale_amount': wholesale_amt,
                'purchase_qty':     month_purchases['qty'] or 0,
                'purchase_amount':  purchase_amt,
                'net':              (sale_amt + wholesale_amt) - purchase_amt,
                'is_curernt':        month_num == today.month,
            })

    context = {
        'tab':                    tab,
        'today':                  today,
        'sales_data':             sales_data,
        'wholesale_data':         wholesale_data,
        'purchase_data':          purchase_data,
        'weekly_data':            weekly_data,
        'monthly_data':           monthly_data,
        'yearly_data':            yearly_data,
        'sale_total_today':       sale_total_today,
        'wholesale_total_today':  wholesale_total_today,
        'purchase_total_today':   purchase_total_today,
    }
    return render(request,'pharmacy/sales-report.html',context)

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
    try:
        medicine = Medicine.objects.get(name__iexact = name)
        return JsonResponse({
            'found':        True,
            'price':        float(medicine.price_per_unit),
            'stock':        medicine.quantity,
            'product_type': medicine.product_type,
        })

    except Medicine.DoesNotExist:
        return JsonResponse({'found': False})

@login_required
def pro_customer_sale(request):
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        total_count = int(request.POST.get('total_count',0))
        discount = float(request.POST.get('discount',0))
        subtotal = float(request.POST.get('subtotal',0))
        final_price = float(request.POST.get('final_price',0))
        errors = []

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
            quantity = request.POST.get(f'sale_{i}_quantity')
            price = request.POST.get(f'sale_{i}_price')
            item_total = request.POST.get(f'sale_{i}_total')
        
            if not name or quantity or not price:
                continue
        
            quantity = int(quantity)
            price = float(price)
            item_total = float(item_total)
        
            try:
                medicine = Medicine.objects.get(name__iexact=name)
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
            ProCustomerSale.objects.create(
                customer= customer,
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
            
            if errors:
                procustomers = ProCustomer.objects.all().order_by('name')
                return render(request,'pharmacy/pro-customer-sale.html',{
                    'errors': errors,
                    'procustomers': procustomers,
                })
            return redirect('pharmacy:pro_customer_sale')
        
    procustomers = ProCustomer.objects.all().order_by('name')                  
    return render(request,'pharmacy/pro-customer-sale.html',{
        'procustomers': procustomers,
    })

@login_required
def pro_customer_report(request):
    current_year = timezone.localdate().year

    # Get every pro customer and annotate with their yearly totals
    customers = ProCustomer.objects.annotate(

        # Total units sold to this customer this year
        total_qty = Sum(
            'orders__quantity_sold',
            filter=Q(orders__sold_at__year=current_year)
        ),

        # Total revenue before discount
        total_subtotal = Sum(
            'orders__subtotal',
            filter=Q(orders__sold_at__year=current_year)
        ),

         # Total discount given
         total_discount = Sum(
            'orders__discount',
            filter=Q(orders__sold_at__year=current_year)
        ),

        # Net amount actually paid — this is what we display
        net_sale = Sum(
            'orders__final_price',
            filter=Q(orders__sold_at__year=current_year)
        ),

        # Count of individual transactions
        order_count = Count(
            'orders',
            filter=Q(orders__sold_at__year=current_year),
            distinct=True
        ),

        # Last purchase date
        last_order=Max('orders__sold_at'),
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
        'current_year': current_year,
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