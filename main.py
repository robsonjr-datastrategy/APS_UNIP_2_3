
import os
from datetime import datetime


# ───────────────────────────────────────────
#  CLASSE: Processo
# ───────────────────────────────────────────

class Processo:
    """Representa um nó do grafo com seus fluxos de energia e massa."""

    def __init__(self, id: str, fluxo_energia: float = 0.0, fluxo_massa: float = 0.0):
        self.id            = id
        self.fluxo_energia = fluxo_energia
        self.fluxo_massa   = fluxo_massa

    def get_fluxo(self) -> float:
        """Retorna o fluxo total (energia + massa) do processo."""
        return self.fluxo_energia + self.fluxo_massa

    def validar(self) -> bool:
        """Valida se os dados do processo são válidos."""
        return (
            bool(self.id.strip()) and
            self.fluxo_energia >= 0 and
            self.fluxo_massa >= 0
        )

    def __repr__(self):
        return f"Processo({self.id}, energia={self.fluxo_energia}, massa={self.fluxo_massa})"


# ───────────────────────────────────────────
#  CLASSE: Grafo
# ───────────────────────────────────────────

class Grafo:
    """
    Representa a rede de processos interconectados.
    Cada aresta é um dicionário {origem: {destino: razao_fluxo}}.
    """

    def __init__(self, minflow: float = 1e-6):
        self.nos:    dict[str, Processo] = {}
        self.arestas: dict[str, dict]   = {}
        self.minflow = minflow

    def adicionar_no(self, processo: Processo):
        """Adiciona um processo como nó do grafo."""
        if not processo.validar():
            raise ValueError(f"Processo '{processo.id}' possui dados inválidos.")
        self.nos[processo.id]    = processo
        self.arestas[processo.id] = {}

    def adicionar_aresta(self, origem: str, destino: str, razao: float):
        """
        Adiciona uma conexão entre dois processos.
        razao: proporção do fluxo que vai de origem para destino (0.0 a 1.0).
        """
        if origem not in self.nos:
            raise ValueError(f"Nó de origem '{origem}' não encontrado.")
        if destino not in self.nos:
            raise ValueError(f"Nó de destino '{destino}' não encontrado.")
        if not (0.0 < razao <= 1.0):
            raise ValueError("A razão do fluxo deve estar entre 0 e 1.")
        self.arestas[origem][destino] = razao

    def construir(self):
        """Valida a estrutura do grafo antes do cálculo."""
        if len(self.nos) < 2:
            raise ValueError("O grafo deve ter pelo menos 2 processos.")
        return True

    def get_vizinhos(self, id_no: str) -> dict:
        """Retorna os vizinhos de um nó e suas razões de fluxo."""
        return self.arestas.get(id_no, {})


# ───────────────────────────────────────────
#  CLASSE: Resultado
# ───────────────────────────────────────────

class Resultado:
    """Armazena os valores de emergia calculados para cada processo."""

    def __init__(self, minflow_usado: float):
        self.valores_emergia: dict[str, float] = {}
        self.emergia_fontes:  dict[str, float] = {}  # apenas fontes independentes
        self.total_emergia:   float            = 0.0
        self.minflow_usado:   float            = minflow_usado

    def adicionar(self, id_no: str, valor: float):
        """Adiciona ou acumula o valor de emergia de um nó."""
        self.valores_emergia[id_no] = self.valores_emergia.get(id_no, 0.0) + valor

    def calcular_total(self):
        """Calcula a emergia total do sistema como soma das fontes independentes."""
        self.total_emergia = sum(self.emergia_fontes.values())

    def get_total(self) -> float:
        return self.total_emergia

    def resumo(self) -> str:
        linhas = ["  Emergia por processo:"]
        for id_no, valor in self.valores_emergia.items():
            linhas.append(f"    {id_no:<20}: {valor:.4f} sej")
        linhas.append("")
        linhas.append("  Fontes independentes:")
        for id_fonte, valor in self.emergia_fontes.items():
            linhas.append(f"    {id_fonte:<20}: {valor:.4f} sej")
        linhas.append(f"  {'Total do sistema':<20}: {self.total_emergia:.4f} sej")
        linhas.append(f"  {'Minflow usado':<20}: {self.minflow_usado:.2e}")
        return "\n".join(linhas)


# ───────────────────────────────────────────
#  CLASSE: CalculadoraEmergia
# ───────────────────────────────────────────

class CalculadoraEmergia:
    """
    Executa o cálculo de emergia usando o algoritmo DFS,
    seguindo as regras da álgebra emergética do SCALE.
    """

    def __init__(self, grafo: Grafo):
        self.grafo     = grafo
        self.resultado = Resultado(grafo.minflow)

    def executar_dfs(self, no_atual: str, emergia_atual: float, visitados: set):
        """
        Percorre o grafo em profundidade (DFS) a partir de um nó fonte.
        Regra 3: distribui emergia proporcionalmente nas divisões.
        Regra 4: não revisita nós no mesmo caminho (evita dupla contagem).
        """
        # Regra 4: não revisitar nós no mesmo caminho
        if no_atual in visitados:
            return

        # Registra emergia no nó atual
        self.resultado.adicionar(no_atual, emergia_atual)

        vizinhos = self.grafo.get_vizinhos(no_atual)

        for destino, razao in vizinhos.items():
            emergia_propagada = emergia_atual * razao

            # Interrompe se emergia abaixo do minflow (otimização)
            if emergia_propagada < self.grafo.minflow:
                continue

            novos_visitados = visitados | {no_atual}
            self.executar_dfs(destino, emergia_propagada, novos_visitados)

    def aplicar_regras(self, nos_fonte: dict):
        """
        Aplica as regras da álgebra emergética para cada fonte.
        Regra 1: toda emergia da fonte é atribuída ao produto de saída.
        Regra 2: coprodutos recebem a emergia total (tratado via DFS independente).
        """
        for id_fonte, emergia_inicial in nos_fonte.items():
            if id_fonte not in self.grafo.nos:
                raise ValueError(f"Nó fonte '{id_fonte}' não encontrado no grafo.")
            self.executar_dfs(id_fonte, emergia_inicial, set())

    def calcular(self, nos_fonte: dict) -> Resultado:
        """
        Executa o cálculo completo de emergia.
        nos_fonte: dicionário {id_no: valor_emergia_inicial}
        O total é a soma das fontes independentes, evitando dupla contagem.
        """
        self.resultado = Resultado(self.grafo.minflow)
        self.resultado.emergia_fontes = dict(nos_fonte)  # registra as fontes
        self.aplicar_regras(nos_fonte)
        self.resultado.calcular_total()
        return self.resultado


# ───────────────────────────────────────────
#  CLASSE: Relatorio
# ───────────────────────────────────────────

class Relatorio:
    """Organiza e exporta os resultados do cálculo de emergia."""

    def __init__(self, resultado: Resultado):
        self.resultado      = resultado
        self.data_geracao   = datetime.now()
        self.formato        = "txt"
        self._conteudo      = ""

    def gerar(self):
        """Monta o conteúdo do relatório."""
        linhas = [
            "=" * 55,
            "  RELATÓRIO DE CÁLCULO DE EMERGIA",
            f"  Gerado em: {self.data_geracao.strftime('%d/%m/%Y %H:%M:%S')}",
            "=" * 55,
            "",
            self.resultado.resumo(),
            "",
            "=" * 55,
        ]
        self._conteudo = "\n".join(linhas)
        print("\n" + self._conteudo)

    def exportar(self) -> str:
        """Salva o relatorio em arquivo .txt e retorna o caminho do arquivo."""
        if not self._conteudo:
            self.gerar()
        pasta_base = os.path.dirname(os.path.abspath(__file__))
        pasta_relatorios = os.path.join(pasta_base, "relatorios")
        os.makedirs(pasta_relatorios, exist_ok=True)

        nome = f"relatorio_emergia_{self.data_geracao.strftime('%Y%m%d_%H%M%S')}.txt"
        caminho = os.path.join(pasta_relatorios, nome)

        with open(caminho, "w", encoding="utf-8") as f:
            f.write(self._conteudo)

        return caminho


# ───────────────────────────────────────────
#  FUNDAMENTAÇÃO TEÓRICA (função main)
# ───────────────────────────────────────────

def exibir_fundamentacao():
    """Exibe o conteúdo explicativo sobre emergia e álgebra emergética."""
    print("""
        FUNDAMENTAÇÃO TEÓRICA — EMERGIA             


O que é Emergia?
  Emergia é um conceito criado pelo ecologista Howard T. Odum
  na década de 1980. Ela quantifica toda a energia solar
  necessária, direta e indiretamente, para produzir um produto
  ou sustentar um sistema. É medida em solar emjoules (sej).

Álgebra Emergética — 4 Regras:
  1. Toda a emergia de entrada é atribuída ao produto de saída.
  2. Em processos com múltiplos produtos (coprodutos), a emergia
     total é atribuída integralmente a cada coproduto.
  3. Quando um fluxo se divide, a emergia é distribuída
     proporcionalmente entre as partes resultantes.
  4. A emergia não pode ser contada duas vezes no mesmo sistema
     (sem dupla contagem de coprodutos e feedbacks).

O algoritmo SCALE (Marvuglia et al., 2013):
  O software representa os processos como um grafo e utiliza
  o algoritmo DFS (Depth-First Search) para percorrer todos
  os caminhos desde as fontes até o produto final, aplicando
  as regras da álgebra emergética em cada nó.
  O parâmetro minflow define o limite mínimo de emergia para
  que um caminho continue sendo explorado.
""")


# ───────────────────────────────────────────
#  INTERFACE DO TERMINAL
# ───────────────────────────────────────────

def limpar():
    os.system("cls" if os.name == "nt" else "clear")


def pausar():
    input("\nPressione ENTER para continuar...")


def cabecalho():
    print("=" * 55)
    print("  SISTEMA DE CÁLCULO DE EMERGIA")
    print("  Baseado no artigo SCALE (Marvuglia et al., 2013)")
    print("=" * 55)
    print()


def menu_principal():
    print("  [1] Inserir dados de entrada")
    print("  [2] Definir minflow")
    print("  [3] Realizar cálculo de emergia")
    print("  [4] Gerar relatório")
    print("  [5] Consultar fundamentação teórica")
    print("  [0] Sair")
    print()


def inserir_dados(grafo: Grafo):
    """UC01 — Manter dados de entrada."""
    limpar()
    print("  INSERIR DADOS DE ENTRADA\n")
    print("  Dica: processos sem conexões de saída são considerados produtos finais.\n")

    while True:
        print(f"  Processos cadastrados: {list(grafo.nos.keys()) or 'nenhum'}")
        print("\n  [1] Adicionar processo")
        print("  [2] Adicionar conexão entre processos")
        print("  [3] Listar processos e conexões")
        print("  [0] Voltar")
        op = input("\n  Opção: ").strip()

        if op == "1":
            id_no = input("  ID do processo: ").strip()
            try:
                energia = float(input("  Fluxo de energia (sej): "))
                massa   = float(input("  Fluxo de massa (g):     "))
                p = Processo(id_no, energia, massa)
                grafo.adicionar_no(p)
                print(f"  ✔ Processo '{id_no}' adicionado.")
            except ValueError as e:
                print(f"  [ERRO] {e}")

        elif op == "2":
            origem  = input("  ID do processo de origem : ").strip()
            destino = input("  ID do processo de destino: ").strip()
            try:
                razao = float(input("  Razão do fluxo (0 a 1)  : "))
                grafo.adicionar_aresta(origem, destino, razao)
                print(f"  ✔ Conexão '{origem}' → '{destino}' adicionada.")
            except ValueError as e:
                print(f"  [ERRO] {e}")

        elif op == "3":
            print("\n  Processos:")
            for p in grafo.nos.values():
                print(f"    {p}")
            print("\n  Conexões:")
            for origem, vizinhos in grafo.arestas.items():
                for destino, razao in vizinhos.items():
                    print(f"    {origem} → {destino} (razão: {razao})")
            if not any(grafo.arestas.values()):
                print("    nenhuma")

        elif op == "0":
            break
        else:
            print("  [ERRO] Opção inválida.")

        pausar()
        limpar()
        print("  INSERIR DADOS DE ENTRADA\n")


def definir_minflow(grafo: Grafo):
    """UC02 — Definir minflow."""
    limpar()
    print("  DEFINIR MINFLOW\n")
    print(f"  Valor atual: {grafo.minflow:.2e}")
    print("  Recomendado para sistemas grandes: 1e-6\n")

    try:
        valor = float(input("  Novo valor de minflow: "))
        if valor <= 0 or valor >= 1:
            print("  [ERRO] O minflow deve ser maior que 0 e menor que 1.")
        else:
            grafo.minflow = valor
            print(f"  ✔ Minflow definido como {valor:.2e}")
    except ValueError:
        print("  [ERRO] Valor inválido. Digite um número decimal.")

    pausar()


def realizar_calculo(grafo: Grafo) -> Resultado | None:
    """UC03 — Realizar cálculo de emergia."""
    limpar()
    print("  REALIZAR CÁLCULO DE EMERGIA\n")

    if len(grafo.nos) < 2:
        print("  [ERRO] Insira pelo menos 2 processos antes de calcular.")
        pausar()
        return None

    print("  Processos disponíveis:", list(grafo.nos.keys()))
    print("\n  Defina os nós fonte e seus valores iniciais de emergia.")
    print("  (Digite 'fim' no ID para encerrar)\n")

    nos_fonte = {}
    while True:
        id_fonte = input("  ID do nó fonte: ").strip()
        if id_fonte.lower() == "fim":
            break
        if id_fonte not in grafo.nos:
            print(f"  [ERRO] Nó '{id_fonte}' não encontrado.")
            continue
        try:
            valor = float(input(f"  Emergia inicial de '{id_fonte}' (sej): "))
            if valor <= 0:
                print("  [ERRO] O valor deve ser maior que 0.")
                continue
            nos_fonte[id_fonte] = valor
        except ValueError:
            print("  [ERRO] Valor inválido.")

    if not nos_fonte:
        print("  [ERRO] Nenhum nó fonte definido.")
        pausar()
        return None

    try:
        grafo.construir()
        calc      = CalculadoraEmergia(grafo)
        resultado = calc.calcular(nos_fonte)

        print("\n  ✔ Cálculo concluído!\n")
        print(resultado.resumo())
        pausar()
        return resultado

    except ValueError as e:
        print(f"\n  [ERRO] {e}")
        pausar()
        return None


def gerar_relatorio(resultado: Resultado | None):
    """UC04 — Gerar relatório."""
    limpar()
    print("  GERAR RELATÓRIO\n")

    if not resultado:
        print("  [ERRO] Nenhum cálculo realizado. Execute o cálculo primeiro.")
        pausar()
        return

    rel = Relatorio(resultado)
    rel.gerar()

    exportar = input("\n  Deseja exportar o relatório para arquivo? (s/n): ").strip().lower()
    if exportar == "s":
        try:
            caminho = rel.exportar()
            print(f"\n  [OK] Relatorio exportado em: {caminho}")
        except OSError as e:
            print(f"\n  [ERRO] Nao foi possivel exportar o relatorio: {e}")

    pausar()


# ───────────────────────────────────────────
#  MAIN
# ───────────────────────────────────────────

def main():
    grafo     = Grafo(minflow=1e-6)
    resultado = None

    while True:
        limpar()
        cabecalho()
        menu_principal()

        op = input("  Opção: ").strip()

        if op == "1":
            inserir_dados(grafo)
        elif op == "2":
            definir_minflow(grafo)
        elif op == "3":
            resultado = realizar_calculo(grafo)
        elif op == "4":
            gerar_relatorio(resultado)
        elif op == "5":
            limpar()
            exibir_fundamentacao()
            pausar()
        elif op == "0":
            limpar()
            print("\n  Sistema encerrado.\n")
            break
        else:
            print("\n  [ERRO] Opção inválida.")
            pausar()


if __name__ == "__main__":
    main()

