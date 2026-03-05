"""
Utility functions for calculating employee payslips.
"""
from datetime import date
from django.db.models import Sum, Q


def get_days_in_month(year, month):
    import calendar
    return calendar.monthrange(year, month)[1]


def compute_payslip(staff_member, month, year):
    """
    Computes a payslip for a staff member for a specific month/year.
    Based on their base salary and scheduled days worked.
    """
    from employees.models import VetSchedule

    # 1. Base Configuration
    try:
        base_salary = float(staff_member.salary)
    except (TypeError, ValueError):
        base_salary = 0.0

    working_days_in_month = 22
    daily_rate = base_salary / working_days_in_month if base_salary else 0

    # 2. Get Shifts Worked (Schedules in the past for that month)
    # Note: For future dates, this acts as a "projected" payslip.
    schedules = VetSchedule.objects.filter(
        staff=staff_member,
        date__year=year,
        date__month=month,
        is_available=True
    ).exclude(shift_type='BREAK')

    # Count unique days worked (a staff might have multiple shifts on one day)
    days_worked = schedules.values('date').distinct().count()

    # 3. Earnings Calculation
    # If they worked all expected days or more, full salary. Otherwise prorated.
    if days_worked >= working_days_in_month:
        gross_pay = base_salary
    else:
        gross_pay = daily_rate * days_worked

    # 4. Standard Deductions (Simulated standard PH deductions)
    # Real HR systems use exact brackets, this is a reasonable simulation for a prototype
    sss_deduction = gross_pay * 0.045 if gross_pay > 0 else 0
    philhealth_deduction = gross_pay * 0.02 if gross_pay > 0 else 0
    pagibig_deduction = 100 if gross_pay > 0 else 0

    total_deductions = sss_deduction + philhealth_deduction + pagibig_deduction

    # 5. Net Pay
    net_pay = gross_pay - total_deductions

    # 6. Build the context dictionary
    month_name = date(year, month, 1).strftime('%B')

    return {
        'staff': staff_member,
        'period': f"{month_name} {year}",
        'base_salary': round(base_salary, 2),
        'daily_rate': round(daily_rate, 2),
        'days_worked': days_worked,
        'gross_pay': round(gross_pay, 2),
        # Deductions
        'sss': round(sss_deduction, 2),
        'philhealth': round(philhealth_deduction, 2),
        'pagibig': round(pagibig_deduction, 2),
        'total_deductions': round(total_deductions, 2),
        # Final
        'net_pay': round(net_pay, 2),
    }
