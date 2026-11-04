#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool 
from mavros_msgs.srv import CommandBool, SetMode, CommandTOL
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import PoseStamped
from rclpy.signals import SignalHandlerOptions
from math import sqrt
import traceback
import time

class Varredura(Node):
    def __init__(self):
        super().__init__('Varredura')
        self.get_logger().info('Esperando conexão com MAVROS...')
        
        self.tempo_inicial = self.get_clock().now()

        # Clientes para os serviços MAVROS
        self.set_mode_client = self.create_client(SetMode, '/mavros/set_mode')
        self.arming_client = self.create_client(CommandBool, '/mavros/cmd/arming')
        self.takeoff_client = self.create_client(CommandTOL, '/mavros/cmd/takeoff')
        self.land_client = self.create_client(CommandTOL, '/mavros/cmd/land')

        #publisher p mandar a mensagem de que a varredura acabou (p tocar os sons)
        self.pub_concluida = self.create_publisher(Bool, '/avant/varredura_concluida', 10)

        #publisher p mandar as coordenadas futuras pro drone
        self.publisher = self.create_publisher(msg_type=PoseStamped, topic="/mavros/setpoint_position/local", qos_profile=qos_profile_sensor_data,)
       
        self.x_atual = None
        self.y_atual = None
        self.z_atual = None
        
        self.etapa_missao = 0
        self.destino_atual = 0
        
        self.waypoints = [(5.4, -1.95, 5.0),(-5.4, -1.95, 5.0),(-5.4, -0.75, 5.0),(5.4, -0.75, 5.0),(5.4, 0.75, 5.0),(-5.4, 0.75, 5.0),(-5.4, 1.95, 5.0),(5.4, 1.95, 5.0),(0.0, 0.0, 5.0)]
        
        #subscriber p ler as posicoes estimadas pelo drone
        self.subscriber = self.create_subscription(msg_type=PoseStamped,
                                                   topic="/mavros/local_position/pose",
                                                   callback=self.ler_posicao,
                                                   qos_profile=qos_profile_sensor_data)

        # Aguarda convexão MAVROS
        # Qualquer service pode ser usado para testar a conexão, não necessariamente o arming
        while rclpy.ok() and not self.arming_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn('Aguardando serviços do MAVROS...')

        # Roda o movimento
        self.get_logger().info('Conexão estabelecida. Iniciando sequência de voo.')
        
        
    def tempo_decorrido(self):
        duracao = self.get_clock().now() - self.tempo_inicial
        return duracao.nanoseconds/1e9
        
    def publicar_ponto(self, ponto):
        x, y, z = ponto
        dado = PoseStamped()
        dado.pose.position.x = x
        dado.pose.position.y = y
        dado.pose.position.z = z
        self.publisher.publish(dado)
        
        
    def ler_posicao(self, msg: PoseStamped):
    
        self.x_atual = msg.pose.position.x
        self.y_atual = msg.pose.position.y
        self.z_atual = msg.pose.position.z
        
        #aq ta subindo
        if self.etapa_missao == 0:
            erro_z = abs (5 - self.z_atual)
            if erro_z < 0.1:
                self.etapa_missao = 1
                self.get_logger().info(f"Entrando na etapa de varredura. Tempo = {self.tempo_decorrido():.1f} segundos")
                self.publicar_ponto (self.waypoints[self.destino_atual])

        #aq ta se movendo pelas positions
        elif self.etapa_missao == 1:
            x_alvo, y_alvo, z_alvo = self.waypoints[self.destino_atual]
            erro_total = sqrt((x_alvo-self.x_atual)**2 + (y_alvo-self.y_atual)**2 + (z_alvo-self.z_atual)**2)
            if erro_total < 0.1:
                self.get_logger().info(f"Chegando ao ponto {self.destino_atual}. Tempo = {self.tempo_decorrido():.1f} segundos")
                self.get_logger().info(f"Erro = {erro_total:.4f}")
                self.destino_atual+=1
                
                if self.destino_atual>=len(self.waypoints):
                    self.etapa_missao = 2
                    self.get_logger().info(f"Preparando para pousar. Tempo = {self.tempo_decorrido():.1f} segundos")
                    self.pub_concluida.publish(Bool(data=True)) #publica que a varredura acabou
                    self.land()
                else:
                    self.publicar_ponto(self.waypoints[self.destino_atual])
                
        #aq ta acabando memo    
        elif self.etapa_missao == 2:
            if self.z_atual < 0.23:
                self.etapa_missao = 3
                self.get_logger().info(f'Missão finalizada. Tempo = {self.tempo_decorrido():.1f} segundos')
        
        self.get_logger().info(f"x = {msg.pose.position.x:.4f}, y = {msg.pose.position.y:.4f}, z = {msg.pose.position.z:.4f}", throttle_duration_sec=1.0)
        

    def set_mode(self, mode_name):
            req = SetMode.Request()
            req.custom_mode = mode_name

            future = self.set_mode_client.call_async(req)
            
            rclpy.spin_until_future_complete(self, future)
            if future.result() is not None and future.result().mode_sent:
                self.get_logger().info(f'Modo {mode_name} definido.')
                return True
            else:
                self.get_logger().error("Falha na configuracao do modo")
                return False

    def arm(self):
        req = CommandBool.Request()
        req.value = True

        future = self.arming_client.call_async(req)
                    
        rclpy.spin_until_future_complete(self, future)
        if future.result() is not None and future.result().success:
            self.get_logger().info(f'Drone armado. Tempo = {self.tempo_decorrido():.1f} segundos')
            return True
        else:
            self.get_logger().error("Falha ao armar o drone")
            return False
            
    def takeoff(self, altitude=5.0):
        req = CommandTOL.Request()
        req.altitude = altitude

        future = self.takeoff_client.call_async(req)
                            
        rclpy.spin_until_future_complete(self, future)
        if future.result() is not None and future.result().success:
            self.get_logger().info(f'Decolando para {altitude} metros. Tempo = {self.tempo_decorrido():.1f} segundos')
            return True
        else:
            self.get_logger().error("Falha para decolar o drone")
            return False
    
    def land(self):
        req = CommandTOL.Request()

        future = self.land_client.call_async(req)

        self.get_logger().info('Pousando...')

    def run_mission(self):
    
        if self.set_mode("GUIDED"):  # modo que permite controle por comandos
            time.sleep(1)

        else:
            return False
            
        if self.arm():
            time.sleep(1)
        else:
            return False

        if self.takeoff(altitude=5.0):
            return True
        else:
            return False
            
    def pouso_de_emergencia(self):

        if self.etapa_missao > 1:
            return
        self.etapa_missao = 2
        self.land()
    
        inicio_espera = self.tempo_decorrido()
    
        while rclpy.ok() and self.etapa_missao < 3 and self.tempo_decorrido()-inicio_espera < 40:
            try:
                rclpy.spin_once(self, timeout_sec=0.1)

            except Exception as erro:
                self.get_logger().error(f"{type(erro).__name__}: {erro}")
                time.sleep(0.1)

        if self.tempo_decorrido()-inicio_espera >= 40:
            self.get_logger().error("O drone pode estar voando ainda")

def main(args=None):
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = None
    try:
        node = Varredura()
        check = node.run_mission()
        if not check:
            return
            
        while rclpy.ok() and node.etapa_missao < 3:
            rclpy.spin_once(node, timeout_sec=0.1)
            
    except Exception:
    
        traceback.print_exc()

        if node is not None:
            node.pouso_de_emergencia()
            
    except KeyboardInterrupt:

        if node is not None:
            node.pouso_de_emergencia()
                
            
    finally:
        if node is not None:
            node.destroy_node()
            
        rclpy.shutdown()

if __name__ == '__main__':
    main()
