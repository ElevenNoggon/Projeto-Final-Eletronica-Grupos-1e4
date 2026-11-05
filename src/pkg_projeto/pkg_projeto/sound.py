#!/usr/bin/env python3
"""Nó de sons: guarda as figuras, ordena pela cor, toca os sons e publica.

Entradas:
  /avant/deteccoes           std_msgs/String (JSON), publicado pelo nó de visão
  /avant/varredura_concluida std_msgs/Bool, publicado pelo nó de varredura
Saída:
  /avant/sequencia_sons      std_msgs/String, ex.: "circulo,hexagono,triangulo"

Formato de cada detecção (JSON):
  {"forma": "circulo|hexagono|triangulo", "cor": "azul|verde|vermelho",
   "x": <m, opcional>, "y": <m, opcional>}
"""
#-------------------------------------------------------------------------#

import json
import os
import shutil
import subprocess
import threading
import time

import rclpy
from ament_index_python.packages import (PackageNotFoundError,
                                         get_package_share_directory)
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, HistoryPolicy, QoSProfile,
                       ReliabilityPolicy)
from std_msgs.msg import Bool, String

from pkg_projeto.memoria import FORMAS, Memoria

ARQUIVOS = {
    'circulo': '1_circulo.mp3',
    'hexagono': '2_hexagono.mp3',
    'triangulo': '3_triangulo.mp3',
}


class SonsNode(Node):
    def __init__(self):
        super().__init__('sons_node')
        self.declare_parameter('topico_deteccoes', '/avant/deteccoes')
        self.declare_parameter('topico_varredura', '/avant/varredura_concluida')
        self.declare_parameter('topico_sequencia', '/avant/sequencia_sons')
        self.declare_parameter('audio_dir', '')
        self.declare_parameter('script_som', '')
        self.declare_parameter('tocar_audio', True)
        self.declare_parameter('min_votos', 5)
        self.declare_parameter('min_proporcao', 0.7)
        self.declare_parameter('min_votos_relaxado', 2)
        self.declare_parameter('pausa_entre_sons', 0.3)
        self.declare_parameter('republicar_segundos', 10.0)

        def par(nome):
            return self.get_parameter(nome).value

        self.mem = Memoria(par('min_votos'), par('min_proporcao'))
        self.min_votos_relaxado = par('min_votos_relaxado')
        self.tocar_audio = par('tocar_audio')
        self.pausa = par('pausa_entre_sons')
        self.republicar_s = par('republicar_segundos')
        self.audio_dir = self._resolver_audio_dir(par('audio_dir'))
        self.script_som = self._resolver_script(par('script_som'))

        qos_det = QoSProfile(reliability=ReliabilityPolicy.RELIABLE,
                             history=HistoryPolicy.KEEP_LAST, depth=100)
        qos_saida = QoSProfile(reliability=ReliabilityPolicy.RELIABLE,
                               durability=DurabilityPolicy.TRANSIENT_LOCAL,
                               history=HistoryPolicy.KEEP_LAST, depth=1)
        self.create_subscription(String, par('topico_deteccoes'),
                                 self._on_deteccao, qos_det)
        self.create_subscription(Bool, par('topico_varredura'),
                                 self._on_varredura, 10)
        self.pub = self.create_publisher(String, par('topico_sequencia'), qos_saida)
        self.create_timer(1.0, self._republicar)

        self._lock = threading.Lock()
        self._iniciado = False
        self._resultado = None
        self._fim_republicacao = 0.0
        self._logadas = set()
        self.get_logger().info(
            f'Nó de sons pronto. Áudios em: {self.audio_dir} | '
            f'script: {self.script_som} (toca_audio={self.tocar_audio})')

    # ------------------------------------------------------------------ entrada
    def _on_deteccao(self, msg):
        if self._iniciado:
            return
        try:
            dado = json.loads(msg.data)
        except (ValueError, TypeError):
            self.get_logger().warn(f'Detecção inválida (não é JSON): {msg.data!r}')
            return
        if not isinstance(dado, dict):
            return
        if self.mem.registrar(dado.get('forma'), dado.get('cor'),
                      cor_hex=dado.get('hex'),
                      x=dado.get('x'), y=dado.get('y')):
            self._atualizar()

    def _on_varredura(self, msg):
        """Fim da varredura sem as 3 figuras: relaxa os critérios e usa o que há."""
        if not msg.data or self._iniciado:
            return
        confirmados = self.mem.confirmados(self.min_votos_relaxado, 0.5)
        if confirmados:
            self.get_logger().warn(
                f'Varredura concluída com {len(confirmados)}/{len(FORMAS)} '
                'figuras (critérios relaxados).')
            self._iniciar(confirmados)
        else:
            self.get_logger().error('Varredura concluída sem nenhuma figura confirmada.')

    def _atualizar(self):
        confirmados = self.mem.confirmados()
        for forma, (cor, votos) in confirmados.items():
            if forma not in self._logadas:
                self._logadas.add(forma)
                self.get_logger().info(
                    f'Figura confirmada: {forma} {cor} ({votos} votos) '
                    f'({len(self._logadas)}/{len(FORMAS)})')
        if len(confirmados) == len(FORMAS):
            self._iniciar(confirmados)

    # ------------------------------------------------------------------ execução
    def _iniciar(self, confirmados):
        with self._lock:
            if self._iniciado:
                return
            self._iniciado = True
        sequencia = self.mem.ordenar(confirmados)

        threading.Thread(target=self._executar, args=(sequencia,confirmados),
                         daemon=True).start()

    def _executar(self, sequencia, confirmados):
        detalhes = []

        for forma in sequencia:
            cor, votos = confirmados[forma]
            valor = self.mem.valor_hex(forma, cor)

            hexadecimal = f'#{valor:06X}' if valor is not None else 'Indisponivel'

            detalhes.append(f'{forma} ({cor} - {hexadecimal} - {votos} votos)')
        self.get_logger().info('Ordem dos sons: ' + ' -> '.join(detalhes))
        for forma in sequencia:
            self.get_logger().info(f'Tocando: {forma}')
            if self.tocar_audio and not self._tocar(forma):
                self.get_logger().error(
                    f'Não foi possível reproduzir o som de "{forma}"; seguindo.')
            time.sleep(self.pausa)
        self._resultado = ','.join(sequencia)
        self._fim_republicacao = time.monotonic() + self.republicar_s
        self._publicar(primeira_vez=True)

    def _publicar(self, primeira_vez=False):
        msg = String()
        msg.data = self._resultado
        self.pub.publish(msg)
        if primeira_vez:
            self.get_logger().info(f'Sequência publicada: {msg.data}')

    def _republicar(self):
        """Repete a mensagem por alguns segundos para quem se inscrever tarde."""
        if self._resultado and time.monotonic() < self._fim_republicacao:
            self._publicar()

    # ------------------------------------------------------------------ áudio
    def _resolver_audio_dir(self, informado):
        if informado:
            return informado
        try:
            return os.path.join(get_package_share_directory('pkg_projeto'), 'audio')
        except PackageNotFoundError:
            return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'audio')

    def _resolver_script(self, informado):
        if informado:
            return informado
        try:
            return os.path.join(get_package_share_directory('pkg_projeto'),
                                'scripts', 'tocar_som.sh')
        except PackageNotFoundError:
            return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scripts', 'tocar_som.sh')

    def _tocar(self, forma):
        """Toca pelo shell script (tocar_som.sh); se ele falhar, tenta em Python."""
        if self._tocar_script(forma):
            return True
        caminho = os.path.join(self.audio_dir, ARQUIVOS[forma])
        if not os.path.isfile(caminho):
            self.get_logger().error(f'Arquivo de áudio não encontrado: {caminho}')
            return False
        return self._tocar_ffmpeg_paplay(caminho) or self._tocar_ffplay(caminho)

    def _tocar_script(self, forma):
        if not os.path.isfile(self.script_som):
            self.get_logger().warn(f'Script de som não encontrado: {self.script_som}')
            return False
        try:
            # 'bash script' dispensa a permissão de execução do arquivo instalado
            r = subprocess.run(['bash', self.script_som, forma, self.audio_dir],
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                               text=True, timeout=90)
        except (OSError, subprocess.TimeoutExpired) as erro:
            self.get_logger().warn(f'Falha ao executar o script de som: {erro}')
            return False
        if r.returncode != 0:
            self.get_logger().warn(
                f'tocar_som.sh terminou com código {r.returncode}: {r.stderr.strip()}')
        return r.returncode == 0

    @staticmethod
    def _tocar_ffmpeg_paplay(caminho):
        if not (shutil.which('ffmpeg') and shutil.which('paplay')):
            return False
        try:
            ff = subprocess.Popen(
                ['ffmpeg', '-loglevel', 'quiet', '-i', caminho, '-f', 'wav', '-'],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            pa = subprocess.Popen(['paplay'], stdin=ff.stdout,
                                  stderr=subprocess.DEVNULL)
            ff.stdout.close()
            try:
                pa.wait(timeout=60)
                ff.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pa.kill()
                ff.kill()
                return False
            return pa.returncode == 0
        except OSError:
            return False

    @staticmethod
    def _tocar_ffplay(caminho):
        if not shutil.which('ffplay'):
            return False
        try:
            resultado = subprocess.run(
                ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', caminho],
                stderr=subprocess.DEVNULL, timeout=60)
            return resultado.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False


def main(args=None):
    rclpy.init(args=args)
    node = SonsNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()