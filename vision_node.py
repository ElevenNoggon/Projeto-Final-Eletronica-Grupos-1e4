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

        self.create_subscription(CameraInfo, '/camera/camera_info',
                                  self.calibracao, 10)
          
        self.create_subscription(Image, '/camera/image_raw',
                                   self.imagens, 10)
                                   
        self.publisher = self.create_publisher(Twist, '/cmd_vel', 10)
        
        self.create_timer(0.05, self.controle)

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

    def medir_base(self, frame, cantos):
            
            centro = np.mean(cantos, axis = 1)
            
            cx, cy = centro[0]
            
            canto_1 = cantos[0,0]	
            canto_2 = cantos[0,1]
            l = np.linalg.norm (canto_2 - canto_1)
            
            x0 = int(np.clip(cx-l, 0, frame.shape[1]))
            x1 = int(np.clip(cx+l, 0, frame.shape[1]))
            y0 = int(np.clip(cy-l, 0, frame.shape[0]))
            y1 = int(np.clip(cy+l, 0, frame.shape[0]))
                
            recorte = frame[y0:y1, x0:x1] 
            if recorte.size == 0:
                return {}
            
            hsv = cv2.cvtColor(recorte, cv2.COLOR_BGR2HSV)
            
            cores = {
                "verde": ([40, 80, 80], [80, 255, 255]),
                "azul": ([90, 80, 80], [130, 255, 255]),
                "vermelho": ([0, 80, 80], [10, 255, 255])}
            resultados = {}

            for nome, (cor_min, cor_max) in cores.items():

                cores_min = np.array(cor_min)
                cores_max = np.array(cor_max)

                mascara = cv2.inRange(hsv, cores_min, cores_max)

                frac_cor = cv2.countNonZero(mascara) / mascara.size

                contornos, _ = cv2.findContours(mascara,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

                circularidade = 0

            
                if contornos:
                
                    contorno_max = max(contornos, key=cv2.contourArea)
                    perimetro = cv2.arcLength(contorno_max, True)
                    area = cv2.contourArea(contorno_max)
                    if perimetro != 0:
                  
                        circularidade = 4 * np.pi * area / perimetro**2

                resultados[nome] = {"fracao": frac_cor,"circularidade": circularidade}
            
            return resultados
    def alvo_detectado(self, frame, cantos):
        
        fracao_verde, redondeza = self.medir_base(frame, cantos)
        
        alvo_certo = fracao_verde >= self.limite_verde and redondeza >= self.limite_redondo
        
        return alvo_certo

def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = TraineeVisionNode()
        while rclpy.ok() and node.pousou == 0:
            rclpy.spin_once(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
                                   