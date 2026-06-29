from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import LoginForm
from .models import Medicine

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
    if not request.user.is_authenticated:
        return redirect('pharmacy:login')
    return render(request,'pharmacy/index.html')

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
                 Medicine.objects.create(
                    name=name,
                    company=company, 
                    product_type=type_,
                    quantity=int(quantity),
                    price_per_unit=float(price),
                    total_price =float(total_price)
                )
        return redirect('pharmacy:add_medicine')
                 
    return render(request,'pharmacy/add-medicine.html')

@login_required
def delete_medicine(request):
    
    search = request.GET.get('search', '')

    if search:
        medicines = Medicine.objects.filter(name__icontains=search)
    else:
        medicines = Medicine.objects.all()

    return render(request, 'pharmacy/delete-medicine.html', {
        'medicines': medicines,
        'search': search,
    })

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
    if not request.user.is_authenticated:
        return redirect('pharmacy:login')
    return render(request,'pharmacy/sale-medicine.html')