from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from decimal import Decimal
import re

def validate_cpf(value):
    """Valida CPF brasileiro"""
    if not value:
        return
    
    # Remove caracteres não numéricos
    cpf = re.sub(r'[^0-9]', '', value)
    
    if len(cpf) != 11:
        raise ValidationError('CPF deve ter 11 dígitos')
    
    # Verifica se todos os dígitos são iguais
    if cpf == cpf[0] * 11:
        raise ValidationError('CPF inválido')
    
    # Validação do primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    if resto < 2:
        digito1 = 0
    else:
        digito1 = 11 - resto
    
    if int(cpf[9]) != digito1:
        raise ValidationError('CPF inválido')
    
    # Validação do segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    if resto < 2:
        digito2 = 0
    else:
        digito2 = 11 - resto
    
    if int(cpf[10]) != digito2:
        raise ValidationError('CPF inválido')

def validate_cnpj(value):
    """Valida CNPJ brasileiro"""
    if not value:
        return
    
    # Remove caracteres não numéricos
    cnpj = re.sub(r'[^0-9]', '', value)
    
    if len(cnpj) != 14:
        raise ValidationError('CNPJ deve ter 14 dígitos')
    
    # Verifica se todos os dígitos são iguais
    if cnpj == cnpj[0] * 14:
        raise ValidationError('CNPJ inválido')
    
    # Validação do primeiro dígito verificador
    multiplicadores1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * multiplicadores1[i] for i in range(12))
    resto = soma % 11
    if resto < 2:
        digito1 = 0
    else:
        digito1 = 11 - resto
    
    if int(cnpj[12]) != digito1:
        raise ValidationError('CNPJ inválido')
    
    # Validação do segundo dígito verificador
    multiplicadores2 = [6, 7, 8, 9, 2, 3, 4, 5, 6, 7, 8, 9]
    soma = sum(int(cnpj[i]) * multiplicadores2[i] for i in range(13))
    resto = soma % 11
    if resto < 2:
        digito2 = 0
    else:
        digito2 = 11 - resto
    
    if int(cnpj[13]) != digito2:
        raise ValidationError('CNPJ inválido')

def validate_cep(value):
    """Valida CEP brasileiro"""
    if not value:
        return
    
    cep = re.sub(r'[^0-9]', '', value)
    if len(cep) != 8:
        raise ValidationError('CEP deve ter 8 dígitos')

def validate_positive_decimal(value):
    """Valida se o valor decimal é positivo"""
    if value is not None and value < 0:
        raise ValidationError('Valor deve ser positivo')

def validate_percentage(value):
    """Valida se o valor está entre 0 e 100 (percentual)"""
    if value is not None and (value < 0 or value > 100):
        raise ValidationError('Percentual deve estar entre 0 e 100')

def validate_empresa_id(value):
    """Valida se o ID da empresa é válido"""
    if value is not None and value <= 0:
        raise ValidationError('ID da empresa deve ser um número positivo')

def validate_phone_number(value):
    """Valida número de telefone brasileiro"""
    if not value:
        return
    
    phone = re.sub(r'[^0-9]', '', value)
    if len(phone) < 10 or len(phone) > 11:
        raise ValidationError('Telefone deve ter 10 ou 11 dígitos')

def validate_email_format(value):
    """Valida formato de email"""
    if not value:
        return
    
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, value):
        raise ValidationError('Formato de email inválido')

# Validators para campos específicos
cpf_validator = RegexValidator(
    regex=r'^\d{11}$',
    message='CPF deve conter apenas 11 dígitos'
)

cnpj_validator = RegexValidator(
    regex=r'^\d{14}$',
    message='CNPJ deve conter apenas 14 dígitos'
)

cep_validator = RegexValidator(
    regex=r'^\d{8}$',
    message='CEP deve conter apenas 8 dígitos'
)

phone_validator = RegexValidator(
    regex=r'^\d{10,11}$',
    message='Telefone deve conter 10 ou 11 dígitos'
)

# Validators para valores monetários
positive_decimal_validator = MinValueValidator(
    Decimal('0.00'),
    message='Valor deve ser positivo'
)

percentage_validator = [
    MinValueValidator(Decimal('0.00'), message='Percentual não pode ser negativo'),
    MaxValueValidator(Decimal('100.00'), message='Percentual não pode ser maior que 100')
]
