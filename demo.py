from NTU.cool import Cool, Fool

c = Cool()
f = Fool(c)

c.new_semester()

# Cool 爬資料
print('請選擇學期:')
print(f'目前: {c.semester}')
print(*c.semesters, sep='  ')

new_semester = input('請選擇學期: ')
c.set_semester(new_semester)

c.update() # 更新該學期的所有課程內容

# Fool 寫成 html
f.nav_update() # 更新導航列，只在註冊課程變動時需要 (如環安衛、加簽、退選、停修等等)
f.build()

print('\n開始下載課程內容附件...')

c.download() # 下載
