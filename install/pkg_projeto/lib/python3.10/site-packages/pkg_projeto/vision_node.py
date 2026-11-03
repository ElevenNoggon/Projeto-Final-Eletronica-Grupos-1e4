import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from sensor_msgs.msg import CameraInfo
from cv_bridge import CvBridge
import cv2
import json
import numpy as np
from std_msgs.msg import String
from geometry_msgs.msg import Twist

class TraineeVisionNode(Node):
    
    def __init__(self):
        super().__init__('trainee_vision_node')

       # self.create_subscription(CameraInfo, '/camera/camera_info',
        #                          self.calibracao, 10)
          
        self.create_subscription(Image, '/camera/image_raw',
                                   self.imagens, 10)
                                   
        self.publisher = self.create_publisher(Twist, '/cmd_vel', 10)
        
        self.pub_deteccoes = self.create_publisher(String, '/avant/deteccoes', 10)
        self.declare_parameter('mostrar_janela', False)
        self.mostrar_janela = self.get_parameter('mostrar_janela').value
        
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
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                
                mascara_cinza = cv2.inRange(hsv,np.array([0, 0, 140]),np.array([180, 35, 255]))
                
                #Detecção por base (a de maior área)
                melhores = {}
                for objeto in resultados:
                    self.get_logger().info(f"Forma: {objeto['forma']} | Cor: {objeto['cor']}") 

                    c = objeto['circulo']
                    if c not in melhores or objeto['area'] > melhores[c]['area']:
                        melhores[c] = objeto

                for objeto in melhores.values():
                    msg = String()
                    msg.data = json.dumps({'forma': objeto['forma'], 'cor': objeto['cor']})
                    self.pub_deteccoes.publish(msg)

                if self.mostrar_janela:
                    cv2.imshow("Deteccao de formas", frame)
                    cv2.imshow("Mascara cinza", mascara_cinza)
                    cv2.waitKey(1)

    def detectar_bases(self, hsv):

    # Detecta as bases cinza-claras
        mascara_cinza = cv2.inRange(
        hsv,
        np.array([0, 0, 140]),
        np.array([180, 35, 255])
    )

        kernel = np.ones((3, 3), np.uint8)

        mascara_cinza = cv2.morphologyEx(
        mascara_cinza,
        cv2.MORPH_CLOSE,
        kernel
    )

        circulos = []

        contornos, _ = cv2.findContours(
        mascara_cinza,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

        for contorno in contornos:

            area = cv2.contourArea(contorno)

            if area < 400:
                continue

            perimetro = cv2.arcLength(contorno, True)

            if perimetro == 0:
                 continue

            circularidade = 4 * np.pi * area / (perimetro ** 2)

            if circularidade > 0.55:

                (cx, cy), raio = cv2.minEnclosingCircle(contorno)

                if raio < 10:
                    continue

                circulos.append((int(cx), int(cy), int(raio)))

                self.get_logger().info(
                f"BASE CINZA ENCONTRADA! "
                f"Centro: ({int(cx)}, {int(cy)}) | "
                f"Raio: {int(raio)}"
            )

        return circulos

    def detectar_formas(self, frame):
            
        
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            circulos = self.detectar_bases(hsv)
            
            cores = {
                "verde": ([40, 80, 80], [80, 255, 255]),
                "azul": ([90, 80, 80], [130, 255, 255])}
            
            resultados = []

            mascara_vermelho_1 = cv2.inRange(
            hsv, np.array([0, 80, 80]), np.array([10, 255, 255]))

            mascara_vermelho_2 = cv2.inRange(hsv, np.array([170, 80, 80]), np.array([179, 255, 255]))

            
  

            for cx, cy ,raio in circulos:

                 cv2.circle(frame,(cx, cy),raio,(0,255,255),2)

                 mascara_roi = np.zeros(hsv.shape[:2], dtype=np.uint8)

                 cv2.circle(mascara_roi,(cx, cy),int(raio * 0.85),255,-1)

                 mascaras = {"verde": cv2.inRange(hsv, np.array(cores["verde"][0]),np.array(cores["verde"][1])),
                                         "azul": cv2.inRange(hsv, np.array(cores["azul"][0]),np.array(cores["azul"][1])),
                                         "vermelho": cv2.bitwise_or(mascara_vermelho_1, mascara_vermelho_2)}
                 



                 for nome_cor, mascara in mascaras.items():

                    mascara = cv2.bitwise_and(mascara, mascara_roi)


                    contornos, _ = cv2.findContours(mascara,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

            
                    for contorno in contornos:

                        area = cv2.contourArea(contorno)

                # Ignora pequenas regioes
                        if area < 300:
                            continue

                        perimetro = cv2.arcLength(contorno, True)
                        aproximacao = cv2.approxPolyDP(contorno,0.04 * perimetro,True)

                        vertices = len(aproximacao)

                        forma = None

                        if vertices == 3:
                            forma = "triangulo"

                        elif vertices == 6:
                            forma = "hexagono"

                        else:
                            circularidade = 0
                            if perimetro > 0:
                                circularidade = (
                    4 * np.pi * area / (perimetro ** 2))

                            if circularidade > 0.80:
                                 forma = "circulo"
                            
                        if forma is not None:
                         # Desenha o contorno e escreve a identificacao
                            cv2.drawContours(frame, [aproximacao], -1, (255, 255, 255), 2)

                            x, y, largura, altura = cv2.boundingRect(aproximacao)

                            texto = f"{forma} {nome_cor}"

                            cv2.putText(frame, texto, (x, y - 10),cv2.FONT_HERSHEY_SIMPLEX, 0.6,(255, 255, 255), 2)

                     
                            resultados.append({"cor": nome_cor,"forma": forma,"area": area,"circulo": (cx, cy, raio)})
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
                                   