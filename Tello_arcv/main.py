#!/usr/bin/env python
# -*- coding: utf-8 -*-
import tello		# tello.pyをインポート
import time			# time.sleepを使いたいので
import cv2			# OpenCVを使うため
import numpy as np

# メイン関数
def main():
	# OpenCVが持つARマーカーライブラリ「aruco」を使う
	aruco = cv2.aruco
	dictionary = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)	# ARマーカーは「4x4ドット，ID番号50まで」の辞書を使う

	# Telloクラスを使って，droneというインスタンス(実体)を作る
	drone = tello.Tello('', 8887, command_timeout=.01)  

	current_time = time.time()	# 現在時刻の保存変数
	pre_time = current_time		# 5秒ごとの'command'送信のための時刻変数

	time.sleep(0.5)		# 通信が安定するまでちょっと待つ


	pre_idno = None		# 前回のID番号を記憶する変数
	count = 0			# 同じID番号が見えた回数を記憶する変数



	# トラックバーを作るため，まず最初にウィンドウを生成
	cv2.namedWindow("OpenCV Window")

	# トラックバーのコールバック関数は何もしない空の関数
	def nothing(x):
		pass

	# トラックバーの生成
	cv2.createTrackbar("H_min", "OpenCV Window", 0, 179, nothing)
	cv2.createTrackbar("H_max", "OpenCV Window", 9, 179, nothing)		# Hueの最大値は179
	cv2.createTrackbar("S_min", "OpenCV Window", 128, 255, nothing)
	cv2.createTrackbar("S_max", "OpenCV Window", 255, 255, nothing)
	cv2.createTrackbar("V_min", "OpenCV Window", 128, 255, nothing)
	cv2.createTrackbar("V_max", "OpenCV Window", 255, 255, nothing)

	flag = 0
	#Ctrl+cが押されるまでループ
	try:
		while True:

			# (A)画像取得
			frame = drone.read()	# 映像を1フレーム取得
			if frame is None or frame.size == 0:	# 中身がおかしかったら無視
				continue 

			# (B)ここから画像処理
			image = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)		# OpenCV用のカラー並びに変換する
			bgr_image = cv2.resize(image, dsize=(480,360) )	# 画像サイズを半分に変更

			hsv_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)	# BGR画像 -> HSV画像

			# トラックバーの値を取る
			h_min = cv2.getTrackbarPos("H_min", "OpenCV Window")
			h_max = cv2.getTrackbarPos("H_max", "OpenCV Window")
			s_min = cv2.getTrackbarPos("S_min", "OpenCV Window")
			s_max = cv2.getTrackbarPos("S_max", "OpenCV Window")
			v_min = cv2.getTrackbarPos("V_min", "OpenCV Window")
			v_max = cv2.getTrackbarPos("V_max", "OpenCV Window")

			# inRange関数で範囲指定２値化
			bin_image = cv2.inRange(hsv_image, (h_min, s_min, v_min), (h_max, s_max, v_max)) # HSV画像なのでタプルもHSV並び

			# bitwise_andで元画像にマスクをかける -> マスクされた部分の色だけ残る
			masked_image = cv2.bitwise_and(hsv_image, hsv_image, mask=bin_image)

			# ラベリング結果書き出し用に画像を準備
			out_image = masked_image

			# 面積・重心計算付きのラベリング処理を行う
			num_labels, label_image, stats, center = cv2.connectedComponentsWithStats(bin_image)

			# 最大のラベルは画面全体を覆う黒なので不要．データを削除
			num_labels = num_labels - 1
			stats = np.delete(stats, 0, 0)
			center = np.delete(center, 0, 0)


			if num_labels >= 1:
				# 面積最大のインデックスを取得
				max_index = np.argmax(stats[:,4])
				#print max_index

				# 面積最大のラベルのx,y,w,h,面積s,重心位置mx,myを得る
				x = stats[max_index][0]
				y = stats[max_index][1]
				w = stats[max_index][2]
				h = stats[max_index][3]
				s = stats[max_index][4]
				mx = int(center[max_index][0])
				my = int(center[max_index][1])
				#print("(x,y)=%d,%d (w,h)=%d,%d s=%d (mx,my)=%d,%d"%(x, y, w, h, s, mx, my) )

				# ラベルを囲うバウンディングボックスを描画
				cv2.rectangle(out_image, (x, y), (x+w, y+h), (255, 0, 255))

				# 重心位置の座標を表示
				#cv2.putText(out_image, "%d,%d"%(mx,my), (x-15, y+h+15), cv2.FONT_HERSHEY_PLAIN, 1, (255, 255, 0))
				cv2.putText(out_image, "%d"%(s), (x, y+h+15), cv2.FONT_HERSHEY_PLAIN, 1, (255, 255, 0))

				if flag == 1:
					a = b = c = d = 0

          # P制御の式(Kpゲインはとりあえず1.0)
					dx = 1.0 * (240 - mx)		# 画面中心との差分

					# 旋回方向の不感帯を設定
					d = 0.0 if abs(dx) < 50.0 else dx   # ±50未満ならゼロにする

					d = -d
					# 旋回方向のソフトウェアリミッタ(±100を超えないように)
					d =  100 if d >  100.0 else d
					d = -100 if d < -100.0 else d

					print('dx=%f'%(dx) )
					drone.send_command('rc %s %s %s %s'%(int(a), int(b), int(c), int(d)) )


# ARマーカーの検出と，枠線の描画
			corners, ids, rejectedImgPoints = aruco.detectMarkers(bgr_image, dictionary) #マーカを検出
			aruco.drawDetectedMarkers(bgr_image, corners, ids, (0,255,0)) #検出したマーカ情報を元に，原画像に描画する

# 50回同じマーカーが見えたらコマンド送信する処理
			try:
				if ids != None:	# idsが空(マーカーが１枚も認識されなかった)場合は何もしない
					idno = ids[0,0]	# idsには複数のマーカーが入っているので，0番目のマーカーを取り出す

					if idno == pre_idno:	# 今回認識したidnoが前回のpre_idnoと同じ時には処理
						count+=1			# 同じマーカーが見えてる限りはカウンタを増やす

						if count > 50:		# 50回同じマーカーが続いたら，コマンドを確定する
							print("ID=%d"%(idno))
							
							if idno == 0:
								drone.takeoff()				# 離陸
							elif idno == 1:
								drone.land()				# 着陸
								time.sleep(3)
							elif idno == 2:
								drone.move_up(0.3)			# 上昇
							elif idno == 3:
								drone.move_down(0.3)		# 下降
							elif idno == 4:
								drone.rotate_ccw(20)		# 左旋回
							elif idno == 5:
								drone.rotate_cw(20)			# 右旋回
							elif idno == 6:
								drone.move_forward(0.3)		# 前進
							elif idno == 7:
								drone.move_backward(0.3)	# 後進
							elif idno == 8:
								drone.move_left(0.3)		# 左移動
							elif idno == 9:
								drone.move_right(0.3)		# 右移動
							
							count = 0	# コマンド送信したらカウント値をリセット
					else:
						count = 0

					pre_idno = idno	# 前回のpre_idnoを更新する
				else:
					count = 0	# 何も見えなくなったらカウント値をリセット

			except ValueError, e:	# if ids != None の処理で時々エラーが出るので，try exceptで捕まえて無視させる
				print("ValueError")








			# (X)ウィンドウに表示
			cv2.imshow('OpenCV Window', out_image)	# ウィンドウに表示するイメージを変えれば色々表示できる

			# (Y)OpenCVウィンドウでキー入力を1ms待つ
			key = cv2.waitKey(1)
			if key == 27:					# k が27(ESC)だったらwhileループを脱出，プログラム終了
				break
			elif key == ord('t'):
				drone.takeoff()				# 離陸
			elif key == ord('l'):
				drone.land()				# 着陸
			elif key == ord('w'):
				drone.move_forward(0.3)		# 前進
			elif key == ord('s'):
				drone.move_backward(0.3)	# 後進
			elif key == ord('a'):
				drone.move_left(0.3)		# 左移動
			elif key == ord('d'):
				drone.move_right(0.3)		# 右移動
			elif key == ord('q'):
				drone.rotate_ccw(20)		# 左旋回
			elif key == ord('e'):
				drone.rotate_cw(20)			# 右旋回
			elif key == ord('r'):
				drone.move_up(0.3)			# 上昇
			elif key == ord('f'):
				drone.move_down(0.3)		# 下降
			elif key == ord('1'):
				flag = 1					# 追跡モードON
			elif key == ord('2'):
				flag = 0					# 追跡モードOFF

			# (Z)5秒おきに'command'を送って、死活チェックを通す
			current_time = time.time()	# 現在時刻を取得
			if current_time - pre_time > 5.0 :	# 前回時刻から5秒以上経過しているか？
				drone.send_command('command')	# 'command'送信
				pre_time = current_time			# 前回時刻を更新

	except( KeyboardInterrupt, SystemExit):    # Ctrl+cが押されたら離脱
		print( "SIGINTを検知" )

	drone.send_command('streamoff')
	# telloクラスを削除
	del drone


# "python main.py"として実行された時だけ動く様にするおまじない処理
if __name__ == "__main__":		# importされると"__main__"は入らないので，実行かimportかを判断できる．
	main()    # メイン関数を実行

