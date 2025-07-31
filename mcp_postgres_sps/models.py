from django.db import models, transaction
from django.db.models import Max
from django.core.exceptions import ValidationError
import logging
from .validators import (
    validate_cpf, validate_cnpj, validate_cep, validate_phone_number,
    validate_email_format, validate_empresa_id, cpf_validator,
    cnpj_validator, cep_validator, phone_validator
)

logger = logging.getLogger(__name__)

class Entidades(models.Model):
    TIPO_ENTIDADES = [
        ('FO', 'FORNECEDOR'),
        ('CL', 'CLIENTE'),
        ('AM', 'AMBOS'),
        ('OU', 'OUTROS'),
        ('VE', 'VENDEDOR'),
        ('FU', 'FUNCIONÁRIOS'),
    ]

    enti_empr = models.IntegerField(
        validators=[validate_empresa_id],
        verbose_name="Empresa",
        help_text="ID da empresa"
    )
    enti_clie = models.BigIntegerField(
        unique=True, 
        primary_key=True,
        verbose_name="Código Cliente"
    )
    enti_nome = models.CharField(
        max_length=100, 
        default='',
        verbose_name="Nome",
        help_text="Nome completo da entidade"
    )
    enti_tipo_enti = models.CharField(
        max_length=100, 
        choices=TIPO_ENTIDADES, 
        default='FO',
        verbose_name="Tipo de Entidade"
    )
    enti_fant = models.CharField(
        max_length=100, 
        default='', 
        blank=True, 
        null=True,
        verbose_name="Nome Fantasia"
    )
    enti_cpf = models.CharField(
        max_length=11, 
        blank=True, 
        null=True,
        validators=[validate_cpf],
        verbose_name="CPF",
        help_text="CPF sem pontuação"
    )
    enti_cnpj = models.CharField(
        max_length=14, 
        blank=True, 
        null=True,
        validators=[validate_cnpj],
        verbose_name="CNPJ",
        help_text="CNPJ sem pontuação"
    )
    enti_insc_esta = models.CharField(
        max_length=11, 
        blank=True, 
        null=True,
        verbose_name="Inscrição Estadual"
    )
    enti_cep = models.CharField(
        max_length=8,
        validators=[validate_cep],
        verbose_name="CEP",
        help_text="CEP sem pontuação"
    )
    enti_ende = models.CharField(
        max_length=60,
        verbose_name="Endereço"
    )
    enti_nume = models.CharField(
        max_length=4,
        verbose_name="Número"
    )
    enti_cida = models.CharField(
        max_length=60,
        verbose_name="Cidade"
    )
    enti_esta = models.CharField(
        max_length=2,
        verbose_name="Estado",
        help_text="Sigla do estado (ex: SP, RJ)"
    )
    enti_fone = models.CharField(
        max_length=14, 
        blank=True, 
        null=True,
        validators=[validate_phone_number],
        verbose_name="Telefone",
        help_text="Telefone sem pontuação"
    )
    enti_celu = models.CharField(
        max_length=15, 
        blank=True, 
        null=True,
        validators=[validate_phone_number],
        verbose_name="Celular",
        help_text="Celular sem pontuação"
    )
    enti_emai = models.CharField(
        max_length=60, 
        blank=True, 
        null=True,
        validators=[validate_email_format],
        verbose_name="Email"
    )  

    def __str__(self):
        return self.enti_nome
    class Meta:
        db_table = 'entidades'
        managed = 'false'


# models.py
from django.db import models


TIPO_FINANCEIRO = [
    ('0', 'À VISTA'),
    ('1', 'A PRAZO'),
    ('2', 'SEM FINANCEIRO'),
]

class PedidosVenda(models.Model):
    pedi_empr = models.IntegerField(verbose_name="Empresa")
    pedi_fili = models.IntegerField(verbose_name="Filial")
    pedi_nume = models.IntegerField(primary_key=True, verbose_name="Número do Pedido")
    
    # Relacionamento com cliente (fornecedor no contexto de venda)
    pedi_forn = models.ForeignKey(
        'Entidades', 
        on_delete=models.PROTECT,
        db_column='pedi_forn',
        related_name='pedidos_como_cliente',
        verbose_name="Cliente",
        limit_choices_to={'enti_tipo_enti__in': ['CL', 'AM']}
    )
    
    pedi_data = models.DateField(verbose_name="Data do Pedido")
    pedi_tota = models.DecimalField(
        decimal_places=2, 
        max_digits=15, 
        verbose_name="Total do Pedido",
        help_text="Valor total do pedido em reais"
    )
    pedi_canc = models.BooleanField(default=False, verbose_name="Cancelado")
    pedi_fina = models.CharField(
        max_length=100, 
        choices=TIPO_FINANCEIRO, 
        default='0',
        verbose_name="Tipo Financeiro"
    )
    
    # Relacionamento com vendedor
    pedi_vend = models.ForeignKey(
        'Entidades',
        on_delete=models.PROTECT,
        db_column='pedi_vend',
        related_name='pedidos_como_vendedor',
        verbose_name="Vendedor",
        limit_choices_to={'enti_tipo_enti': 'VE'},
        null=True,
        blank=True
    )
    
    pedi_stat = models.CharField(
        max_length=50, 
        choices=[
            ('0', 'Pendente'),
            ('1', 'Processando'),
            ('2', 'Enviado'),
            ('3', 'Concluído'),
            ('4', 'Cancelado'),
        ], 
        default='0',
        verbose_name="Status"
    )
    pedi_obse = models.TextField(blank=True, null=True, verbose_name="Observações")

    class Meta:
        db_table = 'pedidosvenda'
        managed = 'false'
        unique_together = ('pedi_empr', 'pedi_fili', 'pedi_nume')

    def __str__(self):
        return f"Pedido {self.pedi_nume} - {self.pedi_forn}"

    
    
class Itenspedidovenda(models.Model):
    iped_empr = models.IntegerField(verbose_name="Empresa")
    iped_fili = models.IntegerField(verbose_name="Filial")
    
    # Relacionamento com pedido
    iped_pedi = models.ForeignKey(
        'PedidosVenda',
        on_delete=models.CASCADE,
        db_column='iped_pedi',
        related_name='itens',
        verbose_name="Pedido"
    )
    
    iped_item = models.IntegerField(verbose_name="Item")
    
    # Relacionamento com produto
    iped_prod = models.ForeignKey(
        'Produtos',
        on_delete=models.PROTECT,
        db_column='iped_prod',
        related_name='itens_vendidos',
        verbose_name="Produto"
    )
    
    iped_quan = models.DecimalField(
        max_digits=15, 
        decimal_places=5, 
        blank=True, 
        null=True,
        verbose_name="Quantidade",
        help_text="Quantidade vendida do produto"
    )
    iped_unit = models.DecimalField(
        max_digits=15, 
        decimal_places=5, 
        blank=True, 
        null=True,
        verbose_name="Preço Unitário"
    )
    iped_suto = models.DecimalField(
        max_digits=15, 
        decimal_places=5, 
        blank=True, 
        null=True,
        verbose_name="Subtotal"
    )
    iped_tota = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        blank=True, 
        null=True,
        verbose_name="Total do Item"
    )
    iped_fret = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        blank=True, 
        null=True,
        verbose_name="Frete"
    )
    iped_desc = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        blank=True, 
        null=True,
        verbose_name="Desconto"
    )
    iped_unli = models.DecimalField(
        max_digits=15, 
        decimal_places=5, 
        blank=True, 
        null=True,
        verbose_name="Unidade Líquida"
    )
    
    # Relacionamentos com fornecedor e vendedor
    iped_forn = models.ForeignKey(
        'Entidades',
        on_delete=models.SET_NULL,
        related_name='itens_fornecidos',
        blank=True,
        null=True,
        verbose_name="Fornecedor",
        limit_choices_to={'enti_tipo_enti__in': ['FO', 'AM']}
    )
    iped_vend = models.ForeignKey(
        'Entidades',
        on_delete=models.SET_NULL,
        related_name='itens_vendidos_por',
        blank=True,
        null=True,
        verbose_name="Vendedor",
        limit_choices_to={'enti_tipo_enti': 'VE'}
    )
    
    iped_cust = models.DecimalField(
        max_digits=15, 
        decimal_places=4, 
        blank=True, 
        null=True,
        verbose_name="Custo"
    )
    iped_tipo = models.IntegerField(blank=True, null=True, verbose_name="Tipo")
    iped_desc_item = models.BooleanField(
        blank=True, 
        null=True,
        verbose_name="Desconto no Item"
    )
    iped_perc_desc = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        blank=True, 
        null=True,
        verbose_name="Percentual de Desconto"
    )
    iped_unme = models.CharField(
        max_length=6, 
        blank=True, 
        null=True,
        verbose_name="Unidade de Medida"
    )
    iped_data = models.DateField(auto_now=True, verbose_name="Data")


    class Meta:
        db_table = 'itenspedidovenda'
        unique_together = (('iped_empr', 'iped_fili', 'iped_pedi', 'iped_item'),)
        managed = 'false'




class PedidosGeral(models.Model):
    empresa = models.IntegerField()
    filial = models.IntegerField()
    numero_pedido = models.IntegerField(primary_key=True)
    codigo_cliente = models.IntegerField()
    nome_cliente = models.CharField(max_length=100)
    data_pedido = models.DateField()
    quantidade_total = models.DecimalField(max_digits=10, decimal_places=2)
    itens_do_pedido = models.TextField()
    valor_total = models.DecimalField(max_digits=12, decimal_places=2)
    tipo_financeiro = models.CharField(max_length=50)
    nome_vendedor = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'pedidos_geral'


from django.db import models
from django.utils.html import mark_safe


class GrupoProduto(models.Model):
    codigo = models.AutoField(
        db_column='grup_codi', 
        primary_key=True,
        verbose_name='Código'
    )
    descricao = models.CharField(
        max_length=255, 
        db_column='grup_desc', 
        verbose_name='Descrição'
    )

    class Meta:
        db_table = 'gruposprodutos'
        verbose_name = 'Grupo de Produto'
        verbose_name_plural = 'Grupos de Produtos'
        managed = 'false'


    def __str__(self):
        return f'{self.codigo} - {self.descricao}'

class SubgrupoProduto(models.Model):
    codigo = models.AutoField(
        db_column='grup_codi', 
        primary_key=True,
        verbose_name='Código'
    )
    descricao = models.CharField(
        max_length=255, 
        db_column='grup_desc', 
        verbose_name='Descrição'
    )

    class Meta:
        db_table = 'subgruposprodutos'
        managed = 'false'



    def __str__(self):
        return self.descricao

class FamiliaProduto(models.Model):
    codigo = models.AutoField(
        db_column='grup_codi', 
        primary_key=True,
        verbose_name='Código'
    )
    descricao = models.CharField(
        max_length=255, 
        db_column='grup_desc', 
        verbose_name='Descrição'
    )

    class Meta:
        db_table = 'familiaprodutos'
        managed = 'false'



    def __str__(self):
        return self.descricao

class Marca(models.Model):
    codigo = models.AutoField(
        db_column='grup_codi', 
        primary_key=True,
        verbose_name='Código'
    )
    nome = models.CharField(
        max_length=255, 
        db_column='grup_desc', 
        verbose_name='Nome'
    )

    class Meta:
        db_table = 'marca'
        managed = 'false'



    def __str__(self):
        return self.nome

class Tabelaprecos(models.Model):
    tabe_empr = models.IntegerField(primary_key=True)  
    tabe_fili = models.IntegerField()
    tabe_prod = models.CharField("Produtos", max_length=60, db_column='tabe_prod')
    tabe_prco = models.DecimalField("Preço", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_icms = models.DecimalField("ICMS", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_desc = models.DecimalField("Desconto", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_vipi = models.DecimalField("Valor IPI", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_pipi = models.DecimalField("% IPI", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_fret = models.DecimalField("Frete", max_digits=15, decimal_places=4, blank=True, null=True)
    tabe_desp = models.DecimalField("Despesas", max_digits=15, decimal_places=4, blank=True, null=True)
    tabe_cust = models.DecimalField("Custo", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_marg = models.DecimalField("Margem", max_digits=15, decimal_places=4, blank=True, null=True)
    tabe_impo = models.DecimalField("Impostos", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_avis = models.DecimalField("Preço à Vista", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_praz = models.DecimalField("Prazo", max_digits=15, decimal_places=4, blank=True, null=True)
    tabe_apra = models.DecimalField("Preço a Prazo", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_vare = models.DecimalField("Varejo", max_digits=15, decimal_places=2, blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True) 
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True) 
    tabe_valo_st = models.DecimalField("Valor ST", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_perc_reaj = models.DecimalField("% Reajuste", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_hist = models.TextField("Histórico", blank=True, null=True)
    tabe_cuge = models.DecimalField("Custo Geral", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_entr = models.DateField("Data Entrada", blank=True, null=True)
    tabe_perc_st = models.DecimalField("% ST", max_digits=7, decimal_places=4, blank=True, null=True)

    class Meta:
        db_table = 'tabelaprecos'
        unique_together = (('tabe_empr', 'tabe_fili', 'tabe_prod'),)
        managed = False
        verbose_name = 'Tabela de Preço'
        verbose_name_plural = 'Tabelas de Preços'

    def __str__(self):
        return f"{self.tabe_prod} - R$ {self.tabe_prco or 0:.2f}"

    @property
    def preco_formatado(self):
        return f"R$ {self.tabe_prco or 0:.2f}"

class UnidadeMedida(models.Model):
    unid_codi = models.CharField(max_length=10, db_column='unid_codi', primary_key=True) 
    unid_desc = models.CharField(max_length=50, db_column='unid_desc') 
    

    class Meta:
        db_table = 'unidadesmedidas'
        managed = 'false'


    def __str__(self):
        return self.unid_desc


class Produtos(models.Model):
    prod_empr = models.CharField(max_length=50, db_column='prod_empr')
    prod_codi = models.CharField(max_length=50, db_column='prod_codi', primary_key=True) 
    prod_nome = models.CharField(max_length=255, db_column='prod_nome') 
    prod_unme = models.ForeignKey(UnidadeMedida,on_delete=models.PROTECT, db_column='prod_unme') 
    prod_grup= models.ForeignKey(GrupoProduto, on_delete=models.DO_NOTHING, db_column='prod_grup', related_name='produtos', blank= True, null= True) 
    prod_sugr = models.ForeignKey(SubgrupoProduto, on_delete=models.DO_NOTHING, db_column='prod_sugr', related_name='produtos', blank= True, null= True) 
    prod_fami= models.ForeignKey(FamiliaProduto, on_delete=models.DO_NOTHING, db_column='prod_fami', related_name='produtos', blank= True, null= True) 
    prod_loca = models.CharField(max_length=255, db_column='prod_loca', blank= True, null= True) 
    prod_ncm = models.CharField(max_length=10, db_column='prod_ncm') 
    prod_marc = models.ForeignKey(Marca, on_delete=models.DO_NOTHING, db_column='prod_marc', related_name='produtos', blank= True, null= True) 
    prod_coba = models.CharField(max_length=50, db_column='prod_coba', blank= True, null= True)
    prod_foto = models.BinaryField(db_column='prod_foto', blank=True, null=True) 



    class Meta:
        db_table = 'produtos'
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        managed = 'false'

    def __str__(self):
        return self.prod_codi
    
    def imagem_tag(self):
        try:
            return mark_safe(f'<img src="{self.foto.url}" width="80" height="80" />')
        except AttributeError:
            return "Sem foto"

    imagem_tag.short_description = 'Imagem'


class SaldoProduto(models.Model):
    produto_codigo = models.ForeignKey(Produtos, on_delete=models.CASCADE, db_column='sapr_prod', primary_key=True)
    empresa = models.CharField(max_length=50, db_column='sapr_empr')
    filial = models.CharField(max_length=50, db_column='sapr_fili')
    saldo_estoque = models.DecimalField(max_digits=10, decimal_places=2, db_column='sapr_sald')

    class Meta:
        db_table = 'saldosprodutos'
        managed = False
        unique_together = (('produto_codigo', 'empresa', 'filial'),)
        constraints = [
            models.UniqueConstraint(
                fields=['produto_codigo', 'empresa', 'filial'],
                name='saldosprodutos_pk'
            )
        ]

    
        




class Tabelaprecoshist(models.Model):
    tabe_id = models.AutoField(primary_key=True)
    tabe_empr = models.IntegerField()
    tabe_fili = models.IntegerField()
    tabe_prod = models.CharField(max_length=20)
    tabe_data_hora = models.DateTimeField()
    tabe_perc_reaj = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_avis_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_avis_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_apra_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_apra_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_hist = models.TextField(blank=True, null=True)
    tabe_prco_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_prco_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_pipi_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_pipi_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_fret_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_fret_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_desp_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_desp_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_cust_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_cust_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_cuge_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_cuge_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_icms_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_icms_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_impo_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_impo_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_marg_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_marg_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_praz_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_praz_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_valo_st_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_valo_st_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tabelaprecoshist'



#Produtos detalhados 
class ProdutosDetalhados(models.Model):
    codigo = models.CharField(max_length=20, primary_key=True)
    nome = models.CharField(max_length=255)
    unidade = models.CharField(max_length=10)
    grupo_id = models.CharField(max_length=20, null=True)
    grupo_nome = models.CharField(max_length=255, null=True)
    marca_id = models.CharField(max_length=20, null=True)
    marca_nome = models.CharField(max_length=255, null=True)
    custo = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    preco_vista = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    preco_prazo = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    saldo = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    foto = models.TextField(null=True)
    peso_bruto = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    peso_liquido = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    empresa = models.CharField(max_length=20, null=True)
    filial = models.CharField(max_length=20, null=True)
    valor_total_estoque = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    valor_total_venda_vista = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    valor_total_venda_prazo = models.DecimalField(max_digits=14, decimal_places=2, null=True)

    class Meta:
        managed = False
        db_table = 'produtos_detalhados'