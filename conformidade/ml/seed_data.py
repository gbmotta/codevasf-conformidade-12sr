"""Exemplos sintéticos / seed para treinar o classificador bootstrap."""

from __future__ import annotations

SEED_EXAMPLES: list[tuple[str, str, str]] = [
    # file_name, content, label
    (
        "OFICIO_001_CODEVASF.pdf",
        "Ofício nº 64/2024. Excelentíssimo Superintendente da CODEVASF. "
        "Requeremos a doação de bens móveis para esta municipalidade.",
        "oficio",
    ),
    (
        "requerimento_associacao.pdf",
        "Ao Superintendente Regional da Codevasf. Vimos requerer a concessão "
        "de equipamento agrícola em doação.",
        "oficio",
    ),
    (
        "CARTAO_CNPJ.pdf",
        "Cadastro Nacional da Pessoa Jurídica CNPJ 12.345.678/0001-90 "
        "NOME EMPRESARIAL ASSOCIACAO EXEMPLO",
        "cnpj",
    ),
    (
        "comprovante_cnpj_rfb.pdf",
        "República Federativa do Brasil. Cadastro Nacional de Pessoas Jurídicas. "
        "Inscrição 00.000.000/0001-91 situação ativa.",
        "cnpj",
    ),
    (
        "CND_RECEITA_FEDERAL.pdf",
        "Certidão Conjunta de Débitos Relativos a Tributos Federais e à Dívida "
        "Ativa da União. Receita Federal. Válida até 15/08/2026.",
        "federal",
    ),
    (
        "certidao_divida_ativa.pdf",
        "Ministério da Fazenda. Certidão de débitos de tributos federais. "
        "Emitida em 10/01/2026. Validade 10/07/2026.",
        "federal",
    ),
    (
        "CRF_FGTS.pdf",
        "Certificado de Regularidade do FGTS - CRF. Caixa Econômica Federal. "
        "Fundo de Garantia do Tempo de Serviço. Válido até 20/09/2026.",
        "fgts",
    ),
    (
        "regularidade_fgts.pdf",
        "FGTS - Certificado de Regularidade. A empresa encontra-se regular "
        "perante o Fundo de Garantia.",
        "fgts",
    ),
    (
        "CNDT.pdf",
        "Certidão Negativa de Débitos Trabalhistas - CNDT. Tribunal Superior "
        "do Trabalho. Válida até 01/12/2026.",
        "cndt",
    ),
    (
        "certidao_trabalhista.pdf",
        "Justiça do Trabalho. Certidão trabalhista negativa. CNDT emitida "
        "pelo Tribunal Superior do Trabalho.",
        "cndt",
    ),
    (
        "ATA_POSSE_PREFEITO.pdf",
        "Ata de Posse. Neste ato transmito o cargo de Prefeito Municipal. "
        "O eleito foi empossado perante a Câmara.",
        "posse",
    ),
    (
        "termo_transmissao_cargo.pdf",
        "Termo de transmissão de cargo. Transmito o cargo ao sucessor eleito "
        "em posse solene.",
        "posse",
    ),
    (
        "DIPLOMA_ELEITORAL.pdf",
        "Diploma. Fica diplomado o eleito Prefeito Municipal para o mandato "
        "eletivo conforme resultado das urnas.",
        "diploma",
    ),
    (
        "diploma_prefeito.pdf",
        "Justiça Eleitoral. Diploma de eleito ao cargo de Prefeito.",
        "diploma",
    ),
    (
        "CNH_REPRESENTANTE.pdf",
        "Carteira Nacional de Habilitação. CPF 123.456.789-09. Registro Geral.",
        "rg_cpf",
    ),
    (
        "RG_CPF_presidente.pdf",
        "Cédula de identidade. CPF do representante legal. Registro Geral SSP.",
        "rg_cpf",
    ),
    (
        "QUITACAO_ELEITORAL.pdf",
        "Certidão de quitação eleitoral. Justiça Eleitoral. Título eleitoral "
        "regular para votação.",
        "eleitoral",
    ),
    (
        "titulo_eleitoral.pdf",
        "Título de eleitor. Quitação eleitoral perante a Justiça Eleitoral.",
        "eleitoral",
    ),
    (
        "COMP_RESIDENCIA.pdf",
        "Comprovante de residência. Conta de energia. Endereço do titular. Consumo kWh.",
        "residencia",
    ),
    (
        "conta_agua_endereco.pdf",
        "Comprovante de endereço. Conta de água. Residência do associado.",
        "residencia",
    ),
    (
        "DECLARACAO_DOACAO_ONEROSA.pdf",
        "Declaro a aceitação à modalidade de Doação Onerosa com contrapartida "
        "de 1% do valor total da doação no ano eleitoral.",
        "doacao_onerosa",
    ),
    (
        "aceitacao_cessao_onerosa.pdf",
        "Aceitação à modalidade de doação onerosa. Contrapartida de 1,5% "
        "do valor total da doação.",
        "doacao_onerosa",
    ),
    (
        "FOR.198_NAO_IMPEDIMENTO.pdf",
        "Declaração de Não Ocorrência de Impedimentos. Declaro que a entidade "
        "não se enquadra nas vedações do art. 39 da Lei nº 13.019/2014. FOR – 198.",
        "impedimento",
    ),
    (
        "FOR-198_impedimentos.pdf",
        "FORMULÁRIO FOR 198. Declaração de não ocorrência de impedimentos "
        "Lei 13.019 art. 39.",
        "impedimento",
    ),
    (
        "FOR.196_PLANO_DE_USO.pdf",
        "Plano de Uso do bem móvel. Destinação social do equipamento. FOR-196.",
        "plano_uso",
    ),
    (
        "plano_uso_trator.pdf",
        "Plano de uso. O bem será destinado às atividades da associação.",
        "plano_uso",
    ),
    (
        "ESTATUTO_SOCIAL.pdf",
        "Estatuto Social da Associação. Assembleia de constituição. Cooperativa.",
        "estatuto",
    ),
    (
        "contrato_social.pdf",
        "Contrato social. Associação civil sem fins lucrativos.",
        "estatuto",
    ),
    (
        "ATA_ELEICAO_DIRETORIA.pdf",
        "Ata de eleição da diretoria. Assembleia elegeu a presidência para o biênio.",
        "ata_diretoria",
    ),
    (
        "ata_criacao_diretoria.pdf",
        "Ata de criação. Eleição da diretoria e posse da presidência.",
        "ata_diretoria",
    ),
    (
        "foto_ilegivel.jpg",
        "",
        "ilegivel",
    ),
    (
        "scan_ruim.pdf",
        "|||| ~~ @@",
        "ilegivel",
    ),
    (
        "anexo_diversos.pdf",
        "Documento anexo sem classificação específica para checklist.",
        "outro",
    ),
    (
        "memorando_interno.pdf",
        "Memorando interno de arquivo morto sem relação direta.",
        "outro",
    ),
]
