import json
import logging
import re
from flask import request, render_template, jsonify, session, g
from tools_me.mysql_tools import SqlData
from tools_me.other_tools import admin_required, sum_code, xianzai_time
from tools_me.parameter import RET, MSG
from tools_me.send_sms.send_sms import CCP
from . import admin_blueprint


@admin_blueprint.route('/acc_to_middle/', methods=['GET', 'POST'])
@admin_required
def acc_to_middle():
    if request.method == 'GET':
        cus_list = SqlData().search_cus_list()
        context = dict()
        context['cus_list'] = cus_list
        return render_template('admin/acc_to_middle.html', **context)
    if request.method == 'POST':
        results = {"code": RET.OK, "msg": MSG.OK}
        data = json.loads(request.form.get('data'))
        name = data.get('name')
        field = data.get('field')
        value = data.get('value')
        bind_cus = data.get('bind_cus')
        del_cus = data.get('del_cus')
        if value:
            if field == 'card_price':
                try:
                    value = float(value)
                    SqlData().update_middle_field_int('card_price', value, name)
                except:
                    return jsonify({'code': RET.SERVERERROR, 'msg': '提成输入值错误!请输入数字类型!'})
            else:
                SqlData().update_middle_field_str(field, value, name)

        if bind_cus:
            middle_id_now = SqlData().search_user_field_name('middle_id', bind_cus)
            # 判断该客户是否已经绑定中介账号
            if middle_id_now:
                results['code'] = RET.SERVERERROR
                results['msg'] = '该客户已经绑定中介!请解绑后重新绑定!'
                return jsonify(results)
            middle_id = SqlData().search_middle_name('id', name)
            user_id = SqlData().search_user_field_name('id', bind_cus)
            SqlData().update_user_field_int('middle_id', middle_id, user_id)
        if del_cus:
            user_id = SqlData().search_user_field_name('id', del_cus)
            middle_id_now = SqlData().search_user_field_name('middle_id', del_cus)
            middle_id = SqlData().search_middle_name('id', name)
            # 判断这个客户是不是当前中介的客户,不是则无权操作
            if middle_id_now != middle_id:
                results['code'] = RET.SERVERERROR
                results['msg'] = '该客户不是当前中介客户!无权删除!'
                return jsonify(results)
            SqlData().update_user_field_int('middle_id', 'NULL', user_id)
        return jsonify(results)


@admin_blueprint.route('/middle_info/', methods=['GET'])
@admin_required
def middle_info():
    page = request.args.get('page')
    limit = request.args.get('limit')
    results = {"code": RET.OK, "msg": MSG.OK, "count": 0, "data": ""}
    task_info = SqlData().search_middle_info()
    if len(task_info) == 0:
        results['MSG'] = MSG.NODATA
        return results
    page_list = list()
    task_info = list(reversed(task_info))
    for i in range(0, len(task_info), int(limit)):
        page_list.append(task_info[i:i + int(limit)])
    results['data'] = page_list[int(page) - 1]
    results['count'] = len(task_info)
    return results


@admin_blueprint.route('/add_middle/', methods=['POST'])
@admin_required
def add_middle():
    results = {"code": RET.OK, "msg": MSG.OK}
    try:
        data = json.loads(request.form.get('data'))
        name = data.get('name')
        account = data.get('account')
        password = data.get('password')
        phone_num = data.get('phone_num')
        create_price = float(data.get('create_price'))
        note = data.get('note1')
        ret = SqlData().search_middle_ed(name)
        if ret:
            results['code'] = RET.SERVERERROR
            results['msg'] = '该中介名已存在!'
            return jsonify(results)
        ret = re.match(r"^1[35789]\d{9}$", phone_num)
        if not ret:
            results['code'] = RET.SERVERERROR
            results['msg'] = '请输入符合规范的电话号码!'
            return jsonify(results)
        SqlData().insert_middle(account, password, name, phone_num, create_price, note)
        return jsonify(results)
    except Exception as e:
        logging.error(e)
        results['code'] = RET.SERVERERROR
        results['msg'] = RET.SERVERERROR
        return jsonify(results)


@admin_blueprint.route('/add_account/', methods=['POST'])
@admin_required
def add_account():
    results = {"code": RET.OK, "msg": MSG.OK}
    try:
        data = json.loads(request.form.get('data'))
        name = data.get('name')
        account = data.get('account')
        password = data.get('password')
        phone_num = data.get('phone_num')
        create_price = float(data.get('create_price'))
        refund = float(data.get('refund'))
        min_top = float(data.get('min_top'))
        max_top = float(data.get('max_top'))
        note = data.get('note')
        ed_name = SqlData().search_user_field_name('account', name)
        if ed_name:
            results['code'] = RET.SERVERERROR
            results['msg'] = '该用户名已存在!'
            return jsonify(results)
        ret = re.match(r"^1[35789]\d{9}$", phone_num)
        if not ret:
            results['code'] = RET.SERVERERROR
            results['msg'] = '请输入符合规范的电话号码!'
            return jsonify(results)
        SqlData().insert_account(account, password, phone_num, name, create_price, refund, min_top, max_top, note)
        return jsonify(results)
    except Exception as e:
        logging.error(e)
        results['code'] = RET.SERVERERROR
        results['msg'] = MSG.SERVERERROR
        return jsonify(results)


@admin_blueprint.route('/change_pass', methods=['GET', 'POST'])
@admin_required
def change_pass():
    if request.method == 'GET':
        return render_template('admin/admin_edit.html')
    if request.method == 'POST':
        results = {"code": RET.OK, "msg": MSG.OK}
        data = json.loads(request.form.get('data'))
        old_pass = data.get('old_pass')
        new_pass_one = data.get('new_pass_one')
        new_pass_two = data.get('new_pass_two')
        if new_pass_two != new_pass_one:
            results['code'] = RET.SERVERERROR
            results['msg'] = '两次输入密码不一致!'
            return jsonify(results)
        password = SqlData().search_admin_field('password')
        if old_pass != password:
            results['code'] = RET.SERVERERROR
            results['msg'] = '密码错误!'
            return jsonify(results)
        SqlData().update_admin_field('password', new_pass_one)
        return jsonify(results)


@admin_blueprint.route('/admin_info', methods=['GET'])
@admin_required
def admin_info():
    account, password, name, balance = SqlData().admin_info()
    context = dict()
    context['account'] = account
    context['password'] = password
    context['name'] = name
    context['balance'] = balance
    return render_template('admin/admin_info.html', **context)


@admin_blueprint.route('/top_history', methods=['GET'])
@admin_required
def top_history():
    page = request.args.get('page')
    limit = request.args.get('limit')
    task_info = SqlData().search_top_history()
    results = {"code": RET.OK, "msg": MSG.OK, "count": 0, "data": ""}
    if len(task_info) == 0:
        results['MSG'] = MSG.NODATA
        return results
    page_list = list()
    task_info = list(reversed(task_info))
    for i in range(0, len(task_info), int(limit)):
        page_list.append(task_info[i:i + int(limit)])
    results['data'] = page_list[int(page) - 1]
    results['count'] = len(task_info)
    return results


@admin_blueprint.route('/top_up', methods=['POST'])
@admin_required
def top_up():
    results = {"code": RET.OK, "msg": MSG.OK}
    try:
        data = request.form.get('money')
        name = request.form.get('name')
        pay_num = sum_code()
        t = xianzai_time()
        money = float(data)
        before = SqlData().search_user_field_name('balance', name)
        balance = before + money
        user_id = SqlData().search_user_field_name('id', name)
        # 更新账户余额
        SqlData().update_user_balance(money, user_id)
        # 更新客户充值记录
        SqlData().insert_top_up(pay_num, t, money, before, balance, user_id)

        phone = SqlData().search_user_field_name('phone_num', name)

        CCP().send_Template_sms(phone, [name, t, money], 478898)

        return jsonify(results)

    except Exception as e:
        logging.error(e)
        results['code'] = RET.SERVERERROR
        results['msg'] = MSG.SERVERERROR
        return jsonify(results)


@admin_blueprint.route('/edit_parameter', methods=['GET', 'POST'])
@admin_required
def edit_parameter():
    if request.method == 'GET':
        return render_template('admin/edit_parameter.html')
    if request.method == 'POST':
        results = {"code": RET.OK, "msg": MSG.OK}
        try:
            data = json.loads(request.form.get('data'))
            name = data.get('name_str')
            create_price = data.get('create_price')
            refund = data.get('refund')
            min_top = data.get('min_top')
            max_top = data.get('max_top')
            if create_price:
                SqlData().update_account_field('create_price', create_price, name)
            if refund:
                SqlData().update_account_field('refund', refund, name)
            if min_top:
                SqlData().update_account_field('min_top', min_top, name)
            if max_top:
                SqlData().update_account_field('max_top', max_top, name)
            return jsonify(results)
        except Exception as e:
            logging.error(e)
            results['code'] = RET.SERVERERROR
            results['msg'] = MSG.SERVERERROR
            return jsonify(results)


@admin_blueprint.route('/account_info', methods=['GET'])
@admin_required
def account_info():
    page = request.args.get('page')
    limit = request.args.get('limit')
    results = {"code": RET.OK, "msg": MSG.OK, "count": 0, "data": ""}
    task_info = SqlData().search_account_info()
    if len(task_info) == 0:
        results['MSG'] = MSG.NODATA
        return results
    page_list = list()
    task_info = list(reversed(task_info))
    for i in range(0, len(task_info), int(limit)):
        page_list.append(task_info[i:i + int(limit)])
    results['data'] = page_list[int(page) - 1]
    results['count'] = len(task_info)
    return results


@admin_blueprint.route('/card_list_html', methods=['GET'])
@admin_required
def card_list_html():
    return render_template('admin/card_list.html')


@admin_blueprint.route('/line_chart', methods=['GET'])
@admin_required
def test():
    l = []
    for i in range(30):
        l.append(i)
    s = []
    for i in range(25, 40):
        s.append(i)
    month = [{'name': 'liuxiao', 'data': l},{'name':'刘总', 'data': s}]
    results = dict()
    results['code'] = RET.OK
    results['msg'] = MSG.OK
    results['data'] = month
    return jsonify(results)


@admin_blueprint.route('/logout', methods=['GET'])
@admin_required
def logout():
    session.pop('admin_id')
    session.pop('admin_name')
    return render_template('user/login.html')


@admin_blueprint.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'GET':
        return render_template('admin/admin_login.html')

    if request.method == 'POST':
        results = dict()
        results['code'] = RET.OK
        results['msg'] = MSG.OK
        try:
            data = json.loads(request.form.get('data'))
            account = data.get('account')
            password = data.get('password')
            admin_id, name = SqlData().search_admin_login(account, password)
            session['admin_id'] = admin_id
            session['admin_name'] = name
            return jsonify(results)

        except Exception as e:
            logging.error(str(e))
            results['code'] = RET.SERVERERROR
            results['msg'] = MSG.PSWDERROR
            return jsonify(results)


@admin_blueprint.route('/', methods=['GET'])
@admin_required
def index():
    admin_name = g.admin_name
    context = dict()
    context['admin_name'] = admin_name
    return render_template('admin/index.html', **context)
