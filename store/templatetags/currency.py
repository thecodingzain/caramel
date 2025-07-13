from django import template

register = template.Library()

@register.filter
def kes(value):
    try:
        # Convert value to float and format it
        value = float(value)
        return f"KSh {value:,.2f}"
    except ValueError:
        return value  # Return the value as is if it's not a valid number

