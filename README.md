# Projeto Final da Eletronica - Grupos 1 e 4

Este é o repositório do projeto final desenvolvido pelos integrantes dos grupos 1 e 4 da área da Eletrônica, no trainee 2026.2 da AVANT.


## **Trainees** 

* Bernardo Pignatti Barbosa
* Evelyn Nogueira Gonçalves
* Lucas Diniz Mendes Miranda


## **Descrição da missão**

Inspirada no desafio “Faulty or not” da última edição da Eletroquad SAE (2026), a tarefa se trata de realizar uma varredura em uma arena de dimensões 8 x 14m a fim de identificar três figuras geométricas e suas colorações, armazenando essas informações na memória do drone. Tais figuras (triângulo, círculo e hexágono) são preenchidas com cores sólidas diferentes (vermelho, verde e azul), estando dispostas, cada uma, dentro de círculos brancos de 800mm de diâmetro, aleatoriamente distribuídos no espaço.

Após encontrar os objetivos, o drone reproduz sons que correspondem ao nome dos três desenhos, na ordem crescente de valores em hexadecimal (em RGB) das cores internas das figuras geométricas.


## **Ambiente de simulação**

Para usar o simulador, faz-se necessária a instalação do container **trainee-26**:

```bash
docker run -it \
  --name trainee-26 \
  --network host \
  --group-add audio \
  --group-add dialout \
  -e DISPLAY=$DISPLAY \
  -e QT_X11_NO_MITSHM=1 \
  -e PULSE_SERVER=unix:/tmp/pulse-socket \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v /run/user/$(id -u)/pulse/native:/tmp/pulse-socket \
  -v /dev/snd:/dev/snd \
  joaoaugustoc/trainee-26:main \
  bash
```
Este comando também roda o container. Após encerrá-lo, para fazer uma nova execução, utiliza-se:

```bash
docker start trainee-26  
```

```bash
docker exec -it trainee-26 bash 
```

Para iniciar a simulação, faz-se uso do script do tmux (já configurado para rodar todas as dependências necessárias):

```bash
cd ~/simulation/starts
./desafio.sh 
```


## **Estrutura do repositório/workspace**

O workspace de ROS 2 que abriga a solução desenvolvida é organizado da seguinte forma:

```bash
Projeto-Final-Eletronica-Grupos-1e4/
├── README.md
└── src/pkg_projeto/
    ├── package.xml, setup.py, setup.cfg, resource/
    ├── launch/missao.launch.xml
    ├── config/sons.yaml
    ├── audio/            1_circulo.mp3  2_hexagono.mp3  3_triangulo.mp3
    ├── scripts/          toca_som.sh
    ├── pkg_projeto/      varredura_pf.py  vision_node.py  sound.py  memoria.py
    └── test/
```

## **Dependências**

As dependências são instaladas por:

```bash
sudo apt install ros-humble-mavros ros-humble-cv-bridge ros-humble-ros-gz-bridge \
                 python3-opencv python3-numpy ffmpeg pulseaudio-utils
```


## **Compilação da solução**

Para compilar, com o workspace do projeto copiado na pasta "starts" do container (path: ~/simulation/starts), usa-se:

```bash
cd ~/simulation/starts/Projeto-Final-Eletronica-Grupos-1e4
colcon build --packages-select pkg_projeto
source install/setup.bash
```


## **Execução**

Para executar a solução, evidentemente, é necessário que a simulação já tenha sido iniciada com o comando `./desafio.sh`. Assim, em outro terminal, com o workspace carregado, faz-se:

```bash
cd ~/simulation/starts/Projeto-Final-Eletronica-Grupos-1e4/src/pkg_projeto/launch
ros2 launch pkg_avant missao.launch.xml
```