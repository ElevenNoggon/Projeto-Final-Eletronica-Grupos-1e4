import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from sensor_msgs.msg import CameraInfo
from cv_bridge import CvBridge
import cv2
import numpy as np
from geometry_msgs.msg import Twist

class TraineeVisionNode(Node):
    
    def __init__(self):
        super().__init__('trainee_vision_node')

       # self.create_subscription(CameraInfo, '/camera/camera_info',
        #                          self.calibracao, 10)
          
        self.create_subscription(Image, '/camera/image_raw',
                                   self.imagens, 10)
                                   
        self.publisher = self.create_publisher(Twist, '/cmd_vel', 10)
        
       # self.create_timer(0.05, self.controle)

        self.k = None
        self.d = None
        self.bridge = CvBridge()
        self.k_impresso = False
        self.limite_redondo = 0.84 



    def calibracao(self, message):
                if not self.k_impresso:
                    self.get_logger().info(f'K = {list(message.k)}')
                    self.k_impresso = True
                    
                self.k = np.array(message.k).reshape(3, 3)
                self.d = np.array(message.d)
        
    def imagens(self, message):
        
                frame = self.bridge.imgmsg_to_cv2(message, desired_encoding='bgr8')
                resultados = self.detectar_formas(frame)
                for objeto in resultados:
                    self.get_logger().info(f"Forma: {objeto['forma']} | Cor: {objeto['cor']}") 
                    cv2.imshow("Deteccao de formas", frame)
                    cv2.waitKey(1)


    def detectar_formas(self, frame):
            
        
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            cores = {
                "verde": ([40, 80, 80], [80, 255, 255]),
                "azul": ([90, 80, 80], [130, 255, 255])}
            
            resultados = []

            mascara_vermelho_1 = cv2.inRange(
            hsv, np.array([0, 80, 80]), np.array([10, 255, 255]))

            mascara_vermelho_2 = cv2.inRange(hsv, np.array([170, 80, 80]), np.array([179, 255, 255]))

            
            mascaras = {"verde": cv2.inRange(hsv, np.array(cores["verde"][0]),np.array(cores["verde"][1])),
                        "azul": cv2.inRange(hsv, np.array(cores["azul"][0]),np.array(cores["azul"][1])),
                        "vermelho": cv2.bitwise_or(mascara_vermelho_1, mascara_vermelho_2)}


            for nome_cor, mascara in mascaras.items():

                contornos, _ = cv2.findContours(mascara,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

            
                for contorno in contornos:

                    area = cv2.contourArea(contorno)

            # Ignora pequenas regiões que podem ser ruídos.
                    if area < 300:
                        continue

                    perimetro = cv2.arcLength(contorno, True)

                    if perimetro == 0:
                         continue

                    aproximacao = cv2.approxPolyDP(contorno,0.04 * perimetro,True)

                    vertices = len(aproximacao)

                    if vertices == 3:
                        forma = "triangulo"

                    elif vertices == 4:
                        x, y, largura, altura = cv2.boundingRect(aproximacao)
                        proporcao = largura / float(altura)

                        if 0.90 <= proporcao <= 1.10:
                            forma = "quadrado"
                        else:
                            forma = "retangulo"

                    elif vertices == 5:
                        forma = "pentagono"

                    elif vertices == 6:
                        forma = "hexagono"

                    else:
                        circularidade = (
                    4 * np.pi * area / (perimetro ** 2))

                        if circularidade > 0.80:
                             forma = "circulo"
                        else:
                             forma = "outra forma"

            # Desenha o contorno e escreve a identificação.
                    cv2.drawContours(
                        frame, [aproximacao], -1, (255, 255, 255), 2
            )

                    x, y, largura, altura = cv2.boundingRect(aproximacao)

                    texto = f"{forma} {nome_cor}"

                    cv2.putText(
                    frame,
                texto,
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

                    resultados.append({
                "cor": nome_cor,
                "forma": forma,
                "area": area
            })

            return resultados

    

def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = TraineeVisionNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
                                   