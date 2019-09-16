% This program will generate a 3D plot 
%                          & best points under different delays
%                          & best point in average

% 3D Tri-Surface Plot
num = xlsread('C:/Users/el17jg/Desktop/GitHub/summer19/cur.csv', 'A2:C716');
x = num(:,1);
y = num(:,2);
z = num(:,3);
K = boundary(x, y, z, 1);
trisurf(K, x, y, z, 'FaceAlpha', 0.1, 'DisplayName', 'Machine g2: 3D TriSurface Plot (stable cases)')
colorbar
xlabel('kp')
ylabel('ki')
zlabel('delay (sec)')
xlim([0.1 3.7]);
ylim([0.01 0.09]);
zlim([0 200]);
set(gca,'XTick',[0.1:0.5:3.7])
set(gca,'YTick',[0.01:0.01:0.09])
set(gca,'ZTick',[0:50:200])



legend show
title('3D TriSurface Plot (stable cases)')